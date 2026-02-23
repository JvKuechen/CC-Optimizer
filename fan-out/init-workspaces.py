"""Phase 1: Deterministic workspace initialization (no LLM)."""
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from config import load_projects_config, resolve_claudes_dir

_user_config_loaded = False
CLAUDES_DIR = resolve_claudes_dir()
WORK_DIR = CLAUDES_DIR / "Work"
PERSONAL_DIR = CLAUDES_DIR / "Personal"
OUTPUT_DIR = Path(__file__).parent / "results"

_projects_cfg = load_projects_config()
SKIP_PROJECTS = set(_projects_cfg.get("init_skip", ["CC-Optimizer"]))

# Baseline permissions - universally safe, stack-agnostic
BASELINE_SETTINGS = {
    "permissions": {
        "allow": [
            "Bash(git status)",
            "Bash(git diff *)",
            "Bash(git log *)",
            "Bash(git branch *)",
            "Bash(ls *)",
            "Bash(pwd)",
            "Bash(cat *)",
            "Bash(head *)",
            "Bash(tail *)",
        ],
        "deny": [
            "Read(.env)",
            "Read(.env.*)",
            "Read(**/credentials*)",
            "Read(**/*secret*)",
        ]
    }
}

## SKIP_PROJECTS loaded from config above


def get_projects():
    """Get all projects from Work/ and Personal/."""
    projects = []

    for base_dir, category in [(WORK_DIR, "work"), (PERSONAL_DIR, "personal")]:
        if not base_dir.exists():
            continue
        for item in base_dir.iterdir():
            if item.is_dir() and item.name not in SKIP_PROJECTS:
                projects.append({
                    "path": str(item),
                    "name": item.name,
                    "category": category,
                })

    return projects


def init_git(project_path: Path) -> dict:
    """Initialize git if not present."""
    git_dir = project_path / ".git"
    if git_dir.exists():
        return {"git": "exists"}

    try:
        result = subprocess.run(
            ["git", "init"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return {"git": "initialized"}
        else:
            return {"git": "error", "error": result.stderr}
    except Exception as e:
        return {"git": "error", "error": str(e)}


def init_claude_dir(project_path: Path) -> dict:
    """Create .claude/ directory with baseline settings."""
    claude_dir = project_path / ".claude"
    settings_file = claude_dir / "settings.json"

    result = {"claude_dir": "exists" if claude_dir.exists() else "created"}

    # Create directory
    claude_dir.mkdir(exist_ok=True)

    # Check if settings already exists
    if settings_file.exists():
        result["settings"] = "exists"
    else:
        # Write baseline settings
        with open(settings_file, "w") as f:
            json.dump(BASELINE_SETTINGS, f, indent=2)
        result["settings"] = "created"

    return result


def check_claude_md(project_path: Path) -> bool:
    """Check if CLAUDE.md exists."""
    return (project_path / "CLAUDE.md").exists()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    projects = get_projects()
    print(f"Found {len(projects)} projects\n")

    results = []
    needs_optimization = []

    for p in projects:
        path = Path(p["path"])
        print(f"Processing: {p['name']} ({p['category']})")

        if args.dry_run:
            has_git = (path / ".git").exists()
            has_claude = (path / ".claude").exists()
            has_claude_md = (path / "CLAUDE.md").exists()
            print(f"  .git: {'exists' if has_git else 'WOULD INIT'}")
            print(f"  .claude/: {'exists' if has_claude else 'WOULD CREATE'}")
            print(f"  CLAUDE.md: {'exists' if has_claude_md else 'NEEDS OPTIMIZATION'}")

            if not has_claude_md:
                needs_optimization.append(p)
            continue

        # Initialize git
        git_result = init_git(path)
        print(f"  git: {git_result['git']}")

        # Initialize .claude/
        claude_result = init_claude_dir(path)
        print(f"  .claude/: {claude_result['claude_dir']}, settings: {claude_result['settings']}")

        # Check if needs optimization
        has_claude_md = check_claude_md(path)
        print(f"  CLAUDE.md: {'exists' if has_claude_md else 'needs optimization'}")

        result = {
            **p,
            "git": git_result,
            "claude": claude_result,
            "has_claude_md": has_claude_md,
            "needs_optimization": not has_claude_md,
        }
        results.append(result)

        if not has_claude_md:
            needs_optimization.append(p)

    print(f"\n=== SUMMARY ===")
    print(f"Total projects: {len(projects)}")
    print(f"Need optimization: {len(needs_optimization)}")

    if not args.dry_run:
        # Save results
        OUTPUT_DIR.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        results_file = OUTPUT_DIR / f"init-results-{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump({
                "timestamp": timestamp,
                "total": len(projects),
                "initialized": len(results),
                "needs_optimization": len(needs_optimization),
                "results": results,
            }, f, indent=2)
        print(f"\nResults saved to: {results_file}")

        queue_file = OUTPUT_DIR / "optimization-queue.json"
        with open(queue_file, "w") as f:
            json.dump({
                "timestamp": timestamp,
                "count": len(needs_optimization),
                "projects": needs_optimization,
            }, f, indent=2)
        print(f"Optimization queue saved to: {queue_file}")


if __name__ == "__main__":
    main()
