"""Wiki documentation fan-out with raw output capture."""
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

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


def load_progress(progress_file: Path) -> set:
    """Load completed projects from progress file."""
    if progress_file.exists():
        with open(progress_file) as f:
            data = json.load(f)
        return set(data.get("completed", []))
    return set()


def save_progress(progress_file: Path, completed: set):
    """Save progress."""
    with open(progress_file, "w") as f:
        json.dump({
            "completed": list(completed),
            "last_updated": datetime.now().isoformat()
        }, f, indent=2)


def run_worker(project: dict, prompt_template: str, timeout: int = 1800) -> dict:
    """Run a single Claude worker and capture raw output."""
    start = time.time()
    project_path = project["path"]

    # Build prompt
    prompt = prompt_template.replace("{{INPUT_PATH}}", project_path)
    prompt = prompt.replace("{{CATEGORY}}", project["category"])

    cmd = [
        "claude",
        "-p", prompt,
        "--model", "opus",
        "--max-turns", "50",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            cwd=project_path
        )

        duration = time.time() - start
        output = result.stdout

        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Exit {result.returncode}: {result.stderr[:500]}",
                "duration": duration,
                "output": output
            }

        return {
            "success": True,
            "output": output,
            "duration": duration
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Timeout after {timeout}s",
            "duration": timeout,
            "output": ""
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "duration": time.time() - start,
            "output": ""
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate wiki docs with raw output capture")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--project", type=str, help="Run on a single project by name")
    parser.add_argument("--concurrent", type=int, default=10)
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    results_dir = base_dir / "results"
    results_dir.mkdir(exist_ok=True)

    # Load prompt template
    with open(base_dir / "workers" / "wiki-raw.md") as f:
        prompt_template = f.read()

    # Discover projects
    projects = discover_projects()
    print(f"Discovered {len(projects)} projects")

    # Filter to single project if specified
    if args.project:
        projects = [p for p in projects if p["name"] == args.project]
        if not projects:
            print(f"Project '{args.project}' not found")
            return

    # Load progress
    progress_file = results_dir / "documentation-raw-progress.json"
    completed = load_progress(progress_file)
    pending = [p for p in projects if p["path"] not in completed]

    if args.limit > 0:
        pending = pending[:args.limit]

    print(f"Pending: {len(pending)} (already done: {len(completed)})")

    if args.dry_run:
        for p in pending:
            print(f"  - {p['name']} ({p['category']})")
        return

    if not pending:
        print("Nothing to do")
        return

    print(f"Running with {args.concurrent} concurrent workers...")

    def process_project(project):
        result = run_worker(project, prompt_template)

        # Save raw output to project directory
        if result["output"]:
            output_path = Path(project["path"]) / "raw-analysis.md"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result["output"])

        return project, result

    with ThreadPoolExecutor(max_workers=args.concurrent) as executor:
        futures = {executor.submit(process_project, p): p for p in pending}

        for future in as_completed(futures):
            project, result = future.result()
            status = "OK" if result["success"] else "FAIL"
            print(f"  [{status}] {project['name']} ({result['duration']:.1f}s)")

            if result["success"]:
                print(f"    Wrote: raw-analysis.md")
            else:
                print(f"    Error: {result.get('error', 'unknown')[:100]}")

            completed.add(project["path"])
            save_progress(progress_file, completed)

    print(f"\nDone. {len(completed)} total completed.")


if __name__ == "__main__":
    main()
