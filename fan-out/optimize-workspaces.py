"""Phase 2: Fan-out workspace optimization using parallel Claude workers."""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent to path for orchestrator import
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import Orchestrator, FanOutConfig


def load_queue(queue_file: Path) -> list:
    """Load the optimization queue."""
    if not queue_file.exists():
        print(f"ERROR: Queue file not found: {queue_file}")
        print("Run init-workspaces.py first to generate the queue.")
        sys.exit(1)

    with open(queue_file) as f:
        data = json.load(f)

    return data.get("projects", [])


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be optimized without running")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of projects to process (0 = all)")
    parser.add_argument("--queue", type=str, default="results/optimization-queue.json",
                        help="Path to queue file")
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    queue_file = base_dir / args.queue

    # Load queue
    projects = load_queue(queue_file)
    print(f"Loaded {len(projects)} projects from queue\n")

    if args.limit > 0:
        projects = projects[:args.limit]
        print(f"Limited to {len(projects)} projects\n")

    if args.dry_run:
        print("=== DRY RUN ===\n")
        for i, p in enumerate(projects, 1):
            print(f"{i}. {p['name']} ({p['category']})")
            print(f"   Path: {p['path']}")
        print(f"\nWould optimize {len(projects)} projects")
        return

    # Load config
    config_file = base_dir / "configs" / "optimize.json"
    with open(config_file) as f:
        config_data = json.load(f)

    config = FanOutConfig(
        worker_prompt_file=str(base_dir / config_data["worker_prompt_file"]),
        model=config_data.get("model", "haiku"),
        max_concurrent=config_data.get("max_concurrent", 5),
        timeout_seconds=config_data.get("timeout_seconds", 180),
        max_turns=config_data.get("max_turns", 10),
        error_recovery=config_data.get("error_recovery"),
        resume_file=str(base_dir / "results" / config_data.get("resume_file", "optimization-progress.json")),
    )

    # Build list of paths for orchestrator
    input_paths = [p["path"] for p in projects]

    print(f"Running orchestrator on {len(projects)} projects...")
    print(f"Config: {config.model}, {config.max_concurrent} concurrent, {config.timeout_seconds}s timeout")
    print(f"Error recovery: {config.error_recovery}\n")

    # Run orchestrator
    orchestrator = Orchestrator(config, base_dir)
    results = orchestrator.run(input_paths)

    # Process results
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_file = base_dir / "results" / f"optimization-results-{timestamp}.json"

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    # Post-process: write files based on worker output
    print("\nWriting files from worker output...")
    for r in successful:
        project_path = Path(r.input_path)
        output = r.output

        # Write CLAUDE.md if content provided
        claude_md_content = output.get("claude_md_content")
        if claude_md_content:
            claude_md_path = project_path / "CLAUDE.md"
            with open(claude_md_path, "w", encoding="utf-8") as f:
                f.write(claude_md_content)
            print(f"  Wrote: {claude_md_path}")

        # Update settings.json with permissions
        permissions = output.get("settings_permissions", [])
        if permissions:
            settings_path = project_path / ".claude" / "settings.json"
            if settings_path.exists():
                with open(settings_path, "r") as f:
                    settings = json.load(f)
                # Merge permissions
                existing = settings.get("permissions", {}).get("allow", [])
                settings["permissions"] = settings.get("permissions", {})
                settings["permissions"]["allow"] = list(set(existing + permissions))
                with open(settings_path, "w") as f:
                    json.dump(settings, f, indent=2)
                print(f"  Updated: {settings_path}")

    summary = {
        "timestamp": timestamp,
        "total": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "results": [
            {
                "path": r.input_path,
                "success": r.success,
                "output": r.output,
                "error": r.error,
                "duration": r.duration_seconds,
            }
            for r in results
        ]
    }

    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n=== SUMMARY ===")
    print(f"Total: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"\nResults saved to: {output_file}")

    if failed:
        print(f"\nFailed projects:")
        for r in failed:
            print(f"  - {r.input_path}: {r.error}")


if __name__ == "__main__":
    main()
