"""Fan-out orchestrator: spawns parallel headless Claude workers."""
import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class WorkerResult:
    """Result from a single worker."""
    input_path: str
    success: bool
    output: dict = field(default_factory=dict)
    error: str = ""
    duration_seconds: float = 0.0


@dataclass
class FanOutConfig:
    """Configuration for a fan-out run."""
    worker_prompt_file: str
    model: str = "haiku"
    max_concurrent: int = 5
    timeout_seconds: int = 120
    max_turns: int = 3
    resume_file: Optional[str] = None
    # Cascading error recovery: list of models to try on failure
    # e.g., ["sonnet", "opus"] means: haiku fails -> try sonnet -> try opus
    error_recovery: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str) -> "FanOutConfig":
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**data)


@dataclass
class WrangleEntry:
    """Log entry for error recovery attempts."""
    input_path: str
    original_model: str
    original_error: str
    recovery_model: str
    recovery_success: bool
    recovery_error: str = ""
    timestamp: str = ""


class Orchestrator:
    """Manages parallel Claude worker execution."""

    def __init__(self, config: FanOutConfig, base_dir: Path):
        self.config = config
        self.base_dir = base_dir
        self.results_dir = base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)

        # Load worker prompt template
        prompt_path = base_dir / config.worker_prompt_file
        with open(prompt_path, "r") as f:
            self.prompt_template = f.read()

        # Progress tracking
        self.completed: set[str] = set()
        self.results: list[WorkerResult] = []
        self.wrangles: list[WrangleEntry] = []  # Error recovery log
        self._load_progress()

    def _load_progress(self):
        """Load progress from resume file if exists."""
        if not self.config.resume_file:
            return
        resume_path = self.results_dir / self.config.resume_file
        if resume_path.exists():
            with open(resume_path, "r") as f:
                data = json.load(f)
            self.completed = set(data.get("completed", []))
            print(f"Resumed: {len(self.completed)} items already processed")

    def _save_progress(self):
        """Save progress for resumability."""
        if not self.config.resume_file:
            return
        resume_path = self.results_dir / self.config.resume_file
        with open(resume_path, "w") as f:
            json.dump({
                "completed": list(self.completed),
                "last_updated": datetime.now().isoformat()
            }, f, indent=2)

    def _run_worker(self, input_path: str, model: Optional[str] = None) -> WorkerResult:
        """Run a single Claude worker."""
        start_time = time.time()
        use_model = model or self.config.model

        # Build the prompt with the specific input
        prompt = self.prompt_template.replace("{{INPUT_PATH}}", input_path)

        # Determine working directory - use the input path if it's a directory
        work_dir = input_path if Path(input_path).is_dir() else str(self.base_dir)

        # Build claude command
        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "json",
            "--model", use_model,
            "--max-turns", str(self.config.max_turns),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace undecodable bytes instead of crashing
                timeout=self.config.timeout_seconds,
                cwd=work_dir
            )

            duration = time.time() - start_time

            if result.returncode != 0:
                return WorkerResult(
                    input_path=input_path,
                    success=False,
                    error=f"Exit code {result.returncode}: {result.stderr[:500]}",
                    duration_seconds=duration
                )

            # Parse JSON output
            try:
                output = json.loads(result.stdout)

                # Check for errors in the response
                if output.get("errors"):
                    errors = output.get("errors", [])
                    # Truncate for readability
                    error_str = str(errors)[:500]
                    return WorkerResult(
                        input_path=input_path,
                        success=False,
                        error=f"Claude errors: {error_str}",
                        duration_seconds=duration
                    )

                # Extract the actual response from Claude's JSON output
                if isinstance(output, dict) and "result" in output:
                    response_text = output.get("result", "")
                else:
                    # No result field - dump the full response for debugging
                    raw_stdout = result.stdout[:2000] if len(result.stdout) > 2000 else result.stdout
                    return WorkerResult(
                        input_path=input_path,
                        success=False,
                        error=f"No result in response",
                        output={"raw_stdout": raw_stdout},
                        duration_seconds=duration
                    )

                # Try to parse the response as JSON (worker should return JSON)
                parsed = self._extract_json(response_text)

                return WorkerResult(
                    input_path=input_path,
                    success=True,
                    output=parsed,
                    duration_seconds=duration
                )
            except json.JSONDecodeError as e:
                return WorkerResult(
                    input_path=input_path,
                    success=False,
                    error=f"JSON parse error: {e}",
                    output={"raw": result.stdout[:1000]},
                    duration_seconds=duration
                )

        except subprocess.TimeoutExpired:
            return WorkerResult(
                input_path=input_path,
                success=False,
                error=f"Timeout after {self.config.timeout_seconds}s",
                duration_seconds=self.config.timeout_seconds
            )
        except Exception as e:
            return WorkerResult(
                input_path=input_path,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time
            )

    def _extract_json(self, text: str) -> dict:
        """Extract JSON object from text that may contain other content."""
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Look for JSON block in markdown
        import re
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Look for raw JSON object
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        return {"raw": text}

    def _run_with_cascade(self, input_path: str) -> WorkerResult:
        """Run worker with cascading error recovery."""
        # Try primary model first
        result = self._run_worker(input_path)

        if result.success or not self.config.error_recovery:
            return result

        # Cascade through recovery models
        original_error = result.error
        for recovery_model in self.config.error_recovery:
            wrangle = WrangleEntry(
                input_path=input_path,
                original_model=self.config.model,
                original_error=original_error,
                recovery_model=recovery_model,
                recovery_success=False,
                timestamp=datetime.now().isoformat()
            )

            print(f"    Retrying with {recovery_model}...")
            result = self._run_worker(input_path, model=recovery_model)

            if result.success:
                wrangle.recovery_success = True
                self.wrangles.append(wrangle)
                return result
            else:
                wrangle.recovery_error = result.error
                self.wrangles.append(wrangle)
                original_error = result.error  # Chain errors for next attempt

        return result  # Return last failure

    def _save_wrangle_log(self):
        """Save error recovery log for later analysis."""
        if not self.wrangles:
            return

        log_path = self.results_dir / "wrangle-log.json"

        # Load existing log if present
        existing = []
        if log_path.exists():
            with open(log_path, "r") as f:
                existing = json.load(f)

        # Append new wrangles
        for w in self.wrangles:
            existing.append({
                "input_path": w.input_path,
                "original_model": w.original_model,
                "original_error": w.original_error,
                "recovery_model": w.recovery_model,
                "recovery_success": w.recovery_success,
                "recovery_error": w.recovery_error,
                "timestamp": w.timestamp
            })

        with open(log_path, "w") as f:
            json.dump(existing, f, indent=2)

        # Summary
        success_count = sum(1 for w in self.wrangles if w.recovery_success)
        fail_count = len(self.wrangles) - success_count
        print(f"  Wrangle log: {success_count} recovered, {fail_count} still failed")

    def run(self, inputs: list[str], on_complete=None) -> list[WorkerResult]:
        """Run workers in parallel for all inputs.

        Args:
            inputs: List of input paths to process
            on_complete: Optional callback(result: WorkerResult) called after each worker completes
        """
        # Filter already completed
        pending = [i for i in inputs if i not in self.completed]

        if not pending:
            print("All inputs already processed")
            return self.results

        print(f"Processing {len(pending)} items ({len(inputs) - len(pending)} already done)")
        print(f"Concurrency: {self.config.max_concurrent}, Model: {self.config.model}")

        with ThreadPoolExecutor(max_workers=self.config.max_concurrent) as executor:
            future_to_input = {
                executor.submit(self._run_with_cascade, input_path): input_path
                for input_path in pending
            }

            for future in as_completed(future_to_input):
                input_path = future_to_input[future]
                try:
                    result = future.result()
                    self.results.append(result)
                    self.completed.add(input_path)
                    self._save_progress()

                    status = "OK" if result.success else "FAIL"
                    print(f"  [{status}] {input_path} ({result.duration_seconds:.1f}s)")

                    # Call callback to handle result immediately (e.g., write files)
                    if on_complete and result.success:
                        try:
                            on_complete(result)
                        except Exception as cb_err:
                            print(f"    Callback error: {cb_err}")

                except Exception as e:
                    print(f"  [ERROR] {input_path}: {e}")

        # Save error recovery log if any wrangles occurred
        self._save_wrangle_log()

        return self.results

    def save_results(self, filename: str):
        """Save all results to a JSON file."""
        output_path = self.results_dir / filename
        with open(output_path, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "model": self.config.model,
                    "max_concurrent": self.config.max_concurrent,
                },
                "summary": {
                    "total": len(self.results),
                    "success": sum(1 for r in self.results if r.success),
                    "failed": sum(1 for r in self.results if not r.success),
                },
                "results": [
                    {
                        "input": r.input_path,
                        "success": r.success,
                        "output": r.output,
                        "error": r.error,
                        "duration_seconds": r.duration_seconds,
                    }
                    for r in self.results
                ]
            }, f, indent=2)
        print(f"Results saved to: {output_path}")
        return output_path


def main():
    parser = argparse.ArgumentParser(description="Fan-out orchestrator")
    parser.add_argument("config", help="Path to config JSON file")
    parser.add_argument("--inputs", nargs="+", help="Input paths to process")
    parser.add_argument("--inputs-file", help="File containing input paths (one per line)")
    parser.add_argument("--output", default="results.json", help="Output filename")

    args = parser.parse_args()

    # Load config
    base_dir = Path(__file__).parent
    config_path = base_dir / "configs" / args.config
    if not config_path.exists():
        config_path = Path(args.config)

    config = FanOutConfig.from_file(str(config_path))

    # Get inputs
    inputs = []
    if args.inputs:
        inputs = args.inputs
    elif args.inputs_file:
        with open(args.inputs_file, "r") as f:
            inputs = [line.strip() for line in f if line.strip()]
    else:
        print("Error: provide --inputs or --inputs-file")
        sys.exit(1)

    # Run orchestrator
    orchestrator = Orchestrator(config, base_dir)
    orchestrator.run(inputs)
    orchestrator.save_results(args.output)


if __name__ == "__main__":
    main()
