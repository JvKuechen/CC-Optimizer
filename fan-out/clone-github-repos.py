"""Clone GitHub repos that don't have local copies."""
import json
import subprocess
from pathlib import Path

from config import load_user_config, load_projects_config, resolve_claudes_dir

# Load configuration
_user_config = load_user_config()
_projects_config = load_projects_config()

CLAUDES_DIR = resolve_claudes_dir(_user_config)
STAGING_DIR = CLAUDES_DIR / "GitHubClones"  # Temporary staging before sorting

GITHUB_USERNAME = _user_config["github_username"]

# Repos we already have locally (different name or path)
SKIP_REPOS = set(_projects_config.get("github_skip_repos", []))

# Work vs Personal classification
WORK_REPOS = set(_projects_config.get("github_work_repos", []))


def get_github_repos():
    """Get list of repos from GitHub."""
    result = subprocess.run(
        ["gh", "repo", "list", GITHUB_USERNAME, "--limit", "100", "--json", "name,isPrivate"],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)


def get_local_projects():
    """Get list of local project names."""
    projects = set()
    for subdir in ["Work", "Personal"]:
        path = CLAUDES_DIR / subdir
        if path.exists():
            for item in path.iterdir():
                if item.is_dir():
                    projects.add(item.name.lower())
    return projects


def clone_repo(repo_name: str, dest_dir: Path, dry_run: bool = True) -> bool:
    """Clone a repo to destination."""
    dest_path = dest_dir / repo_name

    if dest_path.exists():
        print(f"  SKIP (exists): {repo_name}")
        return False

    if dry_run:
        print(f"  WOULD CLONE: gh repo clone {GITHUB_USERNAME}/{repo_name} {dest_path}")
        return True

    try:
        result = subprocess.run(
            ["gh", "repo", "clone", f"{GITHUB_USERNAME}/{repo_name}", str(dest_path)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            print(f"  CLONED: {repo_name}")
            return True
        else:
            print(f"  ERROR: {repo_name}: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ERROR: {repo_name}: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        print("=== DRY RUN MODE ===\n")

    # Get repos
    github_repos = get_github_repos()
    local_projects = get_local_projects()

    print(f"GitHub repos: {len(github_repos)}")
    print(f"Local projects: {len(local_projects)}")

    # Find repos to clone
    to_clone = []
    for repo in github_repos:
        name = repo["name"]
        name_lower = name.lower()

        # Skip if already have locally
        if name_lower in local_projects:
            continue

        # Skip known duplicates
        if name in SKIP_REPOS:
            print(f"SKIP (duplicate): {name}")
            continue

        to_clone.append(repo)

    print(f"\nRepos to clone: {len(to_clone)}\n")

    # Create staging directory
    if not dry_run:
        STAGING_DIR.mkdir(exist_ok=True)

    # Clone repos
    work_count = 0
    personal_count = 0

    print("=== WORK REPOS ===")
    for repo in to_clone:
        name = repo["name"]
        if name in WORK_REPOS:
            dest = CLAUDES_DIR / "Work" if not dry_run else STAGING_DIR
            if clone_repo(name, dest, dry_run):
                work_count += 1

    print("\n=== PERSONAL REPOS ===")
    for repo in to_clone:
        name = repo["name"]
        if name not in WORK_REPOS:
            dest = CLAUDES_DIR / "Personal" if not dry_run else STAGING_DIR
            if clone_repo(name, dest, dry_run):
                personal_count += 1

    print(f"\n=== SUMMARY ===")
    print(f"Work: {work_count}")
    print(f"Personal: {personal_count}")
    print(f"Total: {work_count + personal_count}")

    if dry_run:
        print("\nRun with --execute to actually clone.")


if __name__ == "__main__":
    main()
