"""Wiki documentation fan-out using parallel Opus workers."""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent to path for orchestrator import
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import Orchestrator, FanOutConfig

from config import resolve_claudes_dir

CLAUDES_DIR = resolve_claudes_dir()


def discover_projects() -> list:
    """Discover all projects in Work and Personal directories."""
    projects = []

    for category in ["Work", "Personal"]:
        category_dir = CLAUDES_DIR / category
        if not category_dir.exists():
            continue

        for project_dir in sorted(category_dir.iterdir()):
            if not project_dir.is_dir():
                continue
            if project_dir.name.startswith('.'):
                continue

            projects.append({
                "path": str(project_dir),
                "name": project_dir.name,
                "category": category.lower(),
            })

    return projects


def generate_queue(output_file: Path):
    """Generate documentation queue from discovered projects."""
    projects = discover_projects()

    queue = {
        "generated": datetime.now().isoformat(),
        "total": len(projects),
        "projects": projects
    }

    with open(output_file, "w") as f:
        json.dump(queue, f, indent=2)

    print(f"Generated queue with {len(projects)} projects")
    print(f"  Work: {len([p for p in projects if p['category'] == 'work'])}")
    print(f"  Personal: {len([p for p in projects if p['category'] == 'personal'])}")
    print(f"Saved to: {output_file}")

    return projects


def load_queue(queue_file: Path) -> list:
    """Load the documentation queue."""
    if not queue_file.exists():
        print(f"Queue file not found: {queue_file}")
        print("Generating new queue...")
        return generate_queue(queue_file)

    with open(queue_file) as f:
        data = json.load(f)

    return data.get("projects", [])


class WikiOrchestrator(Orchestrator):
    """Extended orchestrator that handles category placeholder."""

    def __init__(self, config: FanOutConfig, base_dir: Path, projects: list):
        super().__init__(config, base_dir)
        # Build lookup from path to category
        self.category_lookup = {p["path"]: p["category"] for p in projects}

    def _prepare_prompt(self, input_path: str) -> str:
        """Override to inject both INPUT_PATH and CATEGORY."""
        prompt = super()._prepare_prompt(input_path)
        category = self.category_lookup.get(input_path, "unknown")
        return prompt.replace("{{CATEGORY}}", category)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate wiki documentation for all projects")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be documented without running")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of projects to process (0 = all)")
    parser.add_argument("--queue", type=str, default="results/documentation-queue.json",
                        help="Path to queue file")
    parser.add_argument("--generate-queue", action="store_true",
                        help="Regenerate the queue file")
    parser.add_argument("--test", type=int, default=0,
                        help="Run on N test projects only (for validation)")
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    queue_file = base_dir / args.queue

    # Generate queue if requested
    if args.generate_queue:
        generate_queue(queue_file)
        return

    # Load queue
    projects = load_queue(queue_file)
    print(f"Loaded {len(projects)} projects from queue\n")

    # Apply limits
    if args.test > 0:
        # Select diverse test set: some work, some personal
        work = [p for p in projects if p["category"] == "work"][:args.test // 2 + 1]
        personal = [p for p in projects if p["category"] == "personal"][:args.test - len(work)]
        projects = work + personal
        print(f"Test mode: selected {len(projects)} projects")
        for p in projects:
            print(f"  - {p['name']} ({p['category']})")
        print()
    elif args.limit > 0:
        projects = projects[:args.limit]
        print(f"Limited to {len(projects)} projects\n")

    if args.dry_run:
        print("=== DRY RUN ===\n")
        for i, p in enumerate(projects, 1):
            print(f"{i}. {p['name']} ({p['category']})")
            print(f"   Path: {p['path']}")
        print(f"\nWould document {len(projects)} projects")
        return

    # Load config
    config_file = base_dir / "configs" / "document.json"
    with open(config_file) as f:
        config_data = json.load(f)

    config = FanOutConfig(
        worker_prompt_file=str(base_dir / config_data["worker_prompt_file"]),
        model=config_data.get("model", "opus"),
        max_concurrent=config_data.get("max_concurrent", 3),
        timeout_seconds=config_data.get("timeout_seconds", 300),
        max_turns=config_data.get("max_turns", 20),
        error_recovery=config_data.get("error_recovery"),
        resume_file=str(base_dir / "results" / config_data.get("resume_file", "documentation-progress.json")),
    )

    # Build input paths
    input_paths = [p["path"] for p in projects]

    print(f"Running wiki documentation on {len(projects)} projects...")
    print(f"Config: {config.model}, {config.max_concurrent} concurrent, {config.timeout_seconds}s timeout")
    print(f"Error recovery: {config.error_recovery}\n")

    # Track issues for summary
    issues_summary = []

    def write_result_files(result):
        """Callback to write files immediately when each worker completes."""
        project_path = Path(result.input_path)
        output = result.output or {}

        # Write WIKI.md
        wiki_content = output.get("wiki_md_content")
        if wiki_content:
            wiki_path = project_path / "WIKI.md"
            with open(wiki_path, "w", encoding="utf-8") as f:
                f.write(wiki_content)
            print(f"    Wrote: {wiki_path.name}")

        # Write issues.md if present
        issues_content = output.get("issues_md_content")
        if issues_content:
            issues_path = project_path / "issues.md"
            with open(issues_path, "w", encoding="utf-8") as f:
                f.write(issues_content)
            print(f"    Wrote: {issues_path.name}")
            issues_summary.append({
                "project": project_path.name,
                "path": str(project_path),
                "status": output.get("project_status", "unknown"),
            })

    # Run orchestrator with callback for incremental file writing
    orchestrator = WikiOrchestrator(config, base_dir, projects)
    results = orchestrator.run(input_paths, on_complete=write_result_files)

    # Process results for summary
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_file = base_dir / "results" / f"documentation-results-{timestamp}.json"

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    # Build summary
    summary = {
        "timestamp": timestamp,
        "total": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "projects_with_issues": len(issues_summary),
        "issues_summary": issues_summary,
        "results": [
            {
                "path": r.input_path,
                "success": r.success,
                "project_status": r.output.get("project_status") if r.output else None,
                "portfolio_ready": r.output.get("portfolio_ready") if r.output else None,
                "test_results": r.output.get("test_results") if r.output else None,
                "claude_md_issues": r.output.get("claude_md_issues") if r.output else None,
                "summary": r.output.get("summary") if r.output else None,
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
    print(f"Projects with issues: {len(issues_summary)}")
    print(f"\nResults saved to: {output_file}")

    if failed:
        print(f"\nFailed projects:")
        for r in failed:
            print(f"  - {r.input_path}: {r.error}")

    if issues_summary:
        print(f"\nProjects flagged with issues:")
        for item in issues_summary:
            print(f"  - {item['project']} ({item['status']})")


if __name__ == "__main__":
    main()
