"""Continuous queue discovery: no level-by-level waiting."""
import json
import queue
import threading
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class WorkerResult:
    """Result from a single worker."""
    input_path: str
    success: bool
    output: dict = field(default_factory=dict)
    error: str = ""
    duration_seconds: float = 0.0


class ContinuousDiscovery:
    """Continuous queue-based project discovery."""

    def __init__(self, config_path: str = "configs/discovery.json"):
        self.base_dir = Path(__file__).parent
        self.results_dir = self.base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)

        # Load config
        with open(self.base_dir / config_path, "r") as f:
            config = json.load(f)

        self.model = config.get("model", "haiku")
        self.max_concurrent = config.get("max_concurrent", 5)
        self.timeout_seconds = config.get("timeout_seconds", 90)
        self.max_turns = config.get("max_turns", 5)
        self.error_recovery = config.get("error_recovery", [])

        # Load prompt template
        with open(self.base_dir / config.get("worker_prompt_file"), "r") as f:
            self.prompt_template = f.read()

        # Thread-safe data structures
        self.work_queue: queue.Queue = queue.Queue()
        self.projects: list[dict] = []
        self.explored: set[str] = set()
        self.wrangles: list[dict] = []
        self.lock = threading.Lock()

        # Stats
        self.active_workers = 0
        self.total_processed = 0
        self.start_time: float = 0.0

        # State file for resumability
        self.state_file = self.results_dir / "discovery-continuous-state.json"
        self._load_state()

    def _load_state(self):
        """Load state from previous run."""
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                state = json.load(f)
            self.projects = state.get("projects", [])
            self.explored = set(state.get("explored", []))
            pending = state.get("pending", [])
            for p in pending:
                self.work_queue.put(p)
            print(f"Resumed: {len(self.projects)} projects, {len(self.explored)} explored, {len(pending)} pending")

    def _save_state(self):
        """Save state for resumability."""
        pending = []
        # Drain queue to list (then put back)
        while True:
            try:
                item = self.work_queue.get_nowait()
                pending.append(item)
            except queue.Empty:
                break
        # Put items back
        for item in pending:
            self.work_queue.put(item)

        with open(self.state_file, "w") as f:
            json.dump({
                "projects": self.projects,
                "explored": list(self.explored),
                "pending": pending,
                "last_updated": datetime.now().isoformat()
            }, f, indent=2)

    def _normalize_path(self, path: str) -> str:
        """Normalize path for consistent comparison."""
        return str(Path(path).resolve()).replace("\\", "/")

    def _run_worker(self, input_path: str, model: Optional[str] = None) -> WorkerResult:
        """Run a single Claude worker."""
        start_time = time.time()
        use_model = model or self.model

        prompt = self.prompt_template.replace("{{INPUT_PATH}}", input_path)
        work_dir = input_path if Path(input_path).is_dir() else str(self.base_dir)

        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "json",
            "--model", use_model,
            "--max-turns", str(self.max_turns),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=work_dir
            )

            duration = time.time() - start_time

            if result.returncode != 0:
                return WorkerResult(
                    input_path=input_path,
                    success=False,
                    error=f"Exit code {result.returncode}",
                    duration_seconds=duration
                )

            output = json.loads(result.stdout)

            if output.get("errors"):
                return WorkerResult(
                    input_path=input_path,
                    success=False,
                    error=f"Claude errors: {str(output.get('errors'))[:200]}",
                    duration_seconds=duration
                )

            if "result" not in output:
                return WorkerResult(
                    input_path=input_path,
                    success=False,
                    error="No result in response",
                    duration_seconds=duration
                )

            # Extract JSON from response
            response_text = output.get("result", "")
            parsed = self._extract_json(response_text)

            return WorkerResult(
                input_path=input_path,
                success=True,
                output=parsed,
                duration_seconds=duration
            )

        except subprocess.TimeoutExpired:
            return WorkerResult(
                input_path=input_path,
                success=False,
                error=f"Timeout after {self.timeout_seconds}s",
                duration_seconds=self.timeout_seconds
            )
        except Exception as e:
            return WorkerResult(
                input_path=input_path,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time
            )

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from text."""
        import re
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        return {"raw": text}

    def _run_with_cascade(self, input_path: str) -> WorkerResult:
        """Run worker with cascading error recovery."""
        result = self._run_worker(input_path)

        if result.success or not self.error_recovery:
            return result

        original_error = result.error
        for recovery_model in self.error_recovery:
            print(f"    Retrying {Path(input_path).name} with {recovery_model}...")
            result = self._run_worker(input_path, model=recovery_model)

            with self.lock:
                self.wrangles.append({
                    "input_path": input_path,
                    "original_model": self.model,
                    "original_error": original_error,
                    "recovery_model": recovery_model,
                    "recovery_success": result.success,
                    "recovery_error": "" if result.success else result.error,
                    "timestamp": datetime.now().isoformat()
                })

            if result.success:
                return result
            original_error = result.error

        return result

    def _worker_thread(self, _worker_id: int):
        """Worker thread that continuously pulls from queue."""
        while True:
            try:
                input_path = self.work_queue.get(timeout=5)
            except queue.Empty:
                # Check if we should exit
                with self.lock:
                    if self.work_queue.empty() and self.active_workers <= 1:
                        self.active_workers -= 1
                        return
                continue

            with self.lock:
                if input_path in self.explored:
                    self.work_queue.task_done()
                    continue
                self.explored.add(input_path)

            # Process the item
            result = self._run_with_cascade(input_path)

            with self.lock:
                self.total_processed += 1
                status = "OK" if result.success else "FAIL"
                elapsed = time.time() - self.start_time
                rate = self.total_processed / elapsed * 60 if elapsed > 0 else 0
                print(f"  [{status}] {Path(input_path).name} ({result.duration_seconds:.1f}s) "
                      f"[{self.total_processed} done, {self.work_queue.qsize()} queued, {rate:.1f}/min]")

                if result.success:
                    output = result.output

                    # Check if project
                    if output.get("is_project"):
                        project_info = {
                            "path": output.get("path", input_path),
                            "type": output.get("project_type", "unknown"),
                            "markers": output.get("project_markers", []),
                            "name": output.get("project_name", Path(input_path).name),
                            "discovered_at": datetime.now().isoformat()
                        }
                        self.projects.append(project_info)
                        print(f"    PROJECT: {project_info['name']} ({project_info['type']})")

                    # Queue new candidates
                    for candidate in output.get("candidate_subfolders", []):
                        norm = self._normalize_path(candidate)
                        if norm not in self.explored:
                            self.work_queue.put(norm)

                # Save state periodically
                if self.total_processed % 10 == 0:
                    self._save_state()

            self.work_queue.task_done()

    def run(self, start_paths: list[str]):
        """Run continuous discovery."""
        self.start_time = time.time()

        # Add initial paths
        for path in start_paths:
            norm = self._normalize_path(path)
            if norm not in self.explored:
                self.work_queue.put(norm)

        if self.work_queue.empty():
            print("Nothing to explore")
            return self.projects

        print(f"Starting continuous discovery with {self.max_concurrent} workers")
        print(f"Queue size: {self.work_queue.qsize()}, Model: {self.model}")

        # Start worker threads
        threads = []
        self.active_workers = self.max_concurrent
        for i in range(self.max_concurrent):
            t = threading.Thread(target=self._worker_thread, args=(i,), daemon=True)
            t.start()
            threads.append(t)

        # Wait for completion
        for t in threads:
            t.join()

        # Final save
        self._save_state()
        self._save_final_report()
        self._save_wrangle_log()

        return self.projects

    def _save_final_report(self):
        """Save final discovery report."""
        elapsed = time.time() - self.start_time
        report_path = self.results_dir / f"discovery-continuous-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

        by_type: dict[str, list] = {}
        for project in self.projects:
            ptype = project.get("type", "unknown")
            if ptype not in by_type:
                by_type[ptype] = []
            by_type[ptype].append(project)

        report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": elapsed,
            "summary": {
                "total_projects": len(self.projects),
                "folders_explored": len(self.explored),
                "rate_per_minute": self.total_processed / elapsed * 60 if elapsed > 0 else 0,
                "by_type": {k: len(v) for k, v in by_type.items()}
            },
            "projects": self.projects,
            "by_type": by_type
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nFinal report: {report_path}")
        print(f"Total: {len(self.projects)} projects in {len(self.explored)} folders ({elapsed:.0f}s)")
        for ptype, items in sorted(by_type.items(), key=lambda x: -len(x[1])):
            print(f"  {ptype}: {len(items)}")

    def _save_wrangle_log(self):
        """Save error recovery log."""
        if not self.wrangles:
            return

        log_path = self.results_dir / "wrangle-log.json"
        existing = []
        if log_path.exists():
            with open(log_path, "r") as f:
                existing = json.load(f)

        existing.extend(self.wrangles)
        with open(log_path, "w") as f:
            json.dump(existing, f, indent=2)

        success = sum(1 for w in self.wrangles if w["recovery_success"])
        print(f"Wrangle log: {success} recovered, {len(self.wrangles) - success} failed")

    def reset(self):
        """Reset state."""
        self.projects = []
        self.explored = set()
        if self.state_file.exists():
            self.state_file.unlink()
        print("State reset")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Continuous queue discovery")
    parser.add_argument("--start", nargs="+", default=None,
                        help="Starting paths (default: claudes_dir from config)")
    parser.add_argument("--reset", action="store_true", help="Reset state")
    parser.add_argument("--status", action="store_true", help="Show status")

    args = parser.parse_args()

    discovery = ContinuousDiscovery()

    if args.reset:
        discovery.reset()
        return

    if args.status:
        print(f"Projects: {len(discovery.projects)}")
        print(f"Explored: {len(discovery.explored)}")
        print(f"Pending: {discovery.work_queue.qsize()}")
        return

    start_paths = args.start
    if start_paths is None:
        from config import resolve_claudes_dir
        start_paths = [str(resolve_claudes_dir().parent)]

    discovery.run(start_paths)


if __name__ == "__main__":
    main()
