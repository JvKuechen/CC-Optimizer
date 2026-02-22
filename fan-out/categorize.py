"""Categorize discovered projects for consolidation."""
import json
import sys
from pathlib import Path

base_dir = Path(__file__).parent


def find_latest_report(results_dir):
    """Find the most recent discovery report."""
    if not results_dir.exists():
        return None
    reports = sorted(results_dir.glob("discovery-report-*.json"))
    if not reports:
        return None
    return reports[-1]


def main():
    report_path = None

    # Accept explicit path as CLI arg, otherwise find latest
    if len(sys.argv) > 1:
        report_path = Path(sys.argv[1])
    else:
        report_path = find_latest_report(base_dir / "results")

    if report_path is None or not report_path.exists():
        print("ERROR: No discovery report found.", file=sys.stderr)
        print("Run discovery first, or pass report path as argument.", file=sys.stderr)
        sys.exit(1)

    print(f"Using report: {report_path}\n")

    with open(report_path, "r", encoding="utf-8") as f:
        d = json.load(f)

    projects = d["projects"]

    cold_storage = []
    user_home = []
    claudes_existing = []

    for p in projects:
        path = p["path"]
        if "/claudes/" in path:
            claudes_existing.append(p)
        elif "Archive/Projects" in path or "Archive" in path:
            cold_storage.append(p)
        else:
            user_home.append(p)

    print("=== Already in claudes/ (skip) ===")
    print(f"Count: {len(claudes_existing)}")
    for p in claudes_existing:
        print(f"  {p['name']} ({p['type']})")

    print()
    print("=== Cold Storage (to move) ===")
    print(f"Count: {len(cold_storage)}")
    for p in cold_storage:
        print(f"  {p['name']} | {p['type']} | {p['path']}")

    print()
    print("=== User Home (to move) ===")
    print(f"Count: {len(user_home)}")
    for p in user_home:
        print(f"  {p['name']} | {p['type']} | {p['path']}")

    # Check for potential duplicates by name
    all_to_move = cold_storage + user_home
    names = {}
    for p in all_to_move:
        name = p["name"].lower()
        if name not in names:
            names[name] = []
        names[name].append(p)

    duplicates = {k: v for k, v in names.items() if len(v) > 1}

    print()
    print("=== Potential Duplicates (by name) ===")
    print(f"Count: {len(duplicates)}")
    for name, projs in sorted(duplicates.items()):
        print(f"  {name}:")
        for p in projs:
            print(f"    - {p['type']} | {p['path']}")

    # Also check against existing claudes
    existing_names = {p["name"].lower() for p in claudes_existing}
    conflicts = []
    for p in all_to_move:
        if p["name"].lower() in existing_names:
            conflicts.append(p)

    print()
    print("=== Conflicts with existing claudes/ ===")
    print(f"Count: {len(conflicts)}")
    for p in conflicts:
        print(f"  {p['name']} | {p['path']}")


if __name__ == "__main__":
    main()
