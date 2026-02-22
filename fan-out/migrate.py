"""Execute project migration to claudes/Work and claudes/Personal."""
import argparse
import json
import shutil
import sys
from pathlib import Path

# Allow importing config from the fan-out directory
sys.path.insert(0, str(Path(__file__).parent))
from config import load_projects_config, resolve_claudes_dir


def find_latest_report(results_dir):
    """Find the most recent discovery report in results/ directory.

    Returns the path to the latest discovery-report-*.json file,
    or None if no reports exist.
    """
    if not results_dir.exists():
        return None
    reports = sorted(results_dir.glob("discovery-report-*.json"))
    if not reports:
        return None
    return reports[-1]


def is_work_project(name, path, work_indicators, claudes_dir):
    """Determine if project is work-related.

    Args:
        name: Project name
        path: Project source path string
        work_indicators: List of lowercase indicator strings from config
        claudes_dir: Path to claudes directory (for path-based rules)
    """
    name_lower = name.lower()
    path_lower = path.lower()

    for indicator in work_indicators:
        if indicator in name_lower or indicator in path_lower:
            return True

    return False


def migrate_project(src, dest_dir, rename_map, dry_run=True):
    """Move a project to destination directory."""
    src_path = Path(src)
    if not src_path.exists():
        print(f"  SKIP (not found): {src}")
        return False

    # Check for rename mapping, otherwise use folder name
    if src in rename_map:
        project_name = rename_map[src]
        print(f"  RENAME: {src_path.name} -> {project_name}")
    else:
        project_name = src_path.name
    dest_path = dest_dir / project_name

    # Handle name collisions
    if dest_path.exists():
        # Add suffix
        i = 2
        while dest_path.exists():
            dest_path = dest_dir / f"{project_name}_{i}"
            i += 1
        print(f"  RENAME: {project_name} -> {dest_path.name}")

    if dry_run:
        print(f"  DRY RUN: {src} -> {dest_path}")
        return True

    try:
        shutil.move(str(src_path), str(dest_path))
        print(f"  MOVED: {src} -> {dest_path}")
        return True
    except Exception as e:
        print(f"  ERROR: {src}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Migrate discovered projects to claudes/Work and claudes/Personal."
    )
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Show what would be done without moving")
    parser.add_argument("--execute", action="store_true",
                        help="Actually move the files")
    parser.add_argument("--report", type=str, default=None,
                        help="Path to discovery report JSON (default: latest in results/)")
    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        print("=== DRY RUN MODE (use --execute to actually move) ===\n")
    else:
        print("=== EXECUTING MIGRATION ===\n")

    # Load configuration from config files
    projects_cfg = load_projects_config()
    claudes_dir = resolve_claudes_dir()
    work_dir = claudes_dir / "Work"
    personal_dir = claudes_dir / "Personal"

    skip_projects = set(projects_cfg.get("skip_projects", []))
    skip_paths = set(projects_cfg.get("skip_paths", []))
    rename_map = projects_cfg.get("rename_map", {})
    work_indicators = projects_cfg.get("work_indicators", [])
    add_projects = projects_cfg.get("add_projects", [])

    # Find the discovery report
    base_dir = Path(__file__).parent
    if args.report:
        report_path = Path(args.report)
    else:
        report_path = find_latest_report(base_dir / "results")

    if report_path is None or not report_path.exists():
        print("ERROR: No discovery report found.", file=sys.stderr)
        print("Run discovery first, or pass --report <path>.", file=sys.stderr)
        sys.exit(1)

    print(f"Using report: {report_path}\n")

    with open(report_path, "r", encoding="utf-8") as f:
        d = json.load(f)

    projects = d["projects"]

    # Filter to only projects not already in claudes/
    to_migrate = []
    for p in projects:
        path = p["path"]
        name = p["name"]

        # Skip if already in claudes
        if "/claudes/" in path:
            continue

        # Skip if in skip list
        if name in skip_projects:
            print(f"SKIP (in skip list): {name}")
            continue

        # Skip specific paths
        if path in skip_paths:
            print(f"SKIP (duplicate/conflict): {path}")
            continue

        to_migrate.append(p)

    # Add projects that weren't discovered but should be moved
    for p in add_projects:
        if p["path"] not in skip_paths:
            to_migrate.append(p)
            print(f"ADD (parent of discovered subdir): {p['name']}")

    print(f"\nProjects to migrate: {len(to_migrate)}\n")

    # Ensure directories exist
    if not dry_run:
        work_dir.mkdir(exist_ok=True)
        personal_dir.mkdir(exist_ok=True)

    work_count = 0
    personal_count = 0

    print("=== WORK PROJECTS ===")
    for p in to_migrate:
        if is_work_project(p["name"], p["path"], work_indicators, claudes_dir):
            if migrate_project(p["path"], work_dir, rename_map, dry_run):
                work_count += 1

    print("\n=== PERSONAL PROJECTS ===")
    for p in to_migrate:
        if not is_work_project(p["name"], p["path"], work_indicators, claudes_dir):
            if migrate_project(p["path"], personal_dir, rename_map, dry_run):
                personal_count += 1

    print(f"\n=== SUMMARY ===")
    print(f"Work projects: {work_count}")
    print(f"Personal projects: {personal_count}")
    print(f"Total: {work_count + personal_count}")

    if dry_run:
        print("\nRun with --execute to perform the migration.")


if __name__ == "__main__":
    main()
