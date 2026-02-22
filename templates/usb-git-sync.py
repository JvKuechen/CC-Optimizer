"""USB Git Sync - Portable repo sync via USB NVMe drive.

Four commands for the weekend workflow:
  python usb-git-sync.py init    # Friday at work: Create bare repos, push
  python usb-git-sync.py clone   # Friday at home: Clone all repos from USB
  python usb-git-sync.py push    # Sunday at home: Push all changes to USB
  python usb-git-sync.py pull    # Monday at work: Pull all changes from USB

The script auto-detects the USB drive by looking for a .usb-git-sync marker file.
On first run (init), it creates this marker.

Usage:
  python usb-git-sync.py init [--source C:/Users/.../claudes]
  python usb-git-sync.py clone [--dest C:/Users/.../claudes]
  python usb-git-sync.py push [--source C:/Users/.../claudes]
  python usb-git-sync.py pull [--dest C:/Users/.../claudes]
"""

import argparse
import shutil
import string
import subprocess
import sys
from pathlib import Path

MARKER_FILE = ".usb-git-sync"
REPOS_DIR = "repos"
DEFAULT_SOURCE = Path.home() / "claudes"


def find_usb_drive():
    """Find the USB drive by looking for the marker file on Windows drives."""
    # Check common removable drive letters first, then all others
    priority_letters = ["D", "E", "F", "G", "H"]
    other_letters = [c for c in string.ascii_uppercase if c not in priority_letters and c != "C"]

    for letter in priority_letters + other_letters:
        drive = Path(f"{letter}:/")
        marker = drive / MARKER_FILE
        if marker.exists():
            print(f"Found USB drive: {letter}:/")
            return drive

    return None


def find_usb_drive_for_init():
    """Find a drive that looks like the USB (has repos dir or is empty-ish)."""
    # For init, we need to find the drive even without marker
    # Look for D: first since user mentioned it
    for letter in ["D", "E", "F", "G", "H"]:
        drive = Path(f"{letter}:/")
        if drive.exists():
            # Check if it already has our repos or marker
            if (drive / MARKER_FILE).exists() or (drive / REPOS_DIR).exists():
                return drive
            # Check if drive is accessible and relatively empty (likely USB)
            try:
                contents = list(drive.iterdir())
                # If it has less than 20 items, probably a USB drive
                if len(contents) < 20:
                    response = input(f"Use {letter}:/ as USB drive? (y/n): ").strip().lower()
                    if response == "y":
                        return drive
            except PermissionError:
                continue

    # Ask user to specify
    letter = input("Enter USB drive letter (e.g., D): ").strip().upper()
    if letter:
        return Path(f"{letter}:/")
    return None


def run_git(args, cwd=None, check=True):
    """Run a git command and return the result."""
    cmd = ["git"] + args
    print(f"  > git {' '.join(args)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"    Error: {result.stderr.strip()}")
        return False
    return True


def get_repos(source_dir, max_depth=4):
    """Get list of git repos in source directory (searches up to max_depth levels)."""
    repos = []

    def scan(path, depth):
        if depth > max_depth:
            return
        try:
            for item in path.iterdir():
                if item.is_dir():
                    if (item / ".git").exists():
                        repos.append(item)
                    elif not item.name.startswith("."):
                        scan(item, depth + 1)
        except PermissionError:
            pass

    scan(source_dir, 0)
    return sorted(repos)


def cmd_init(args):
    """Initialize bare repos on USB and push all branches."""
    source = Path(args.source).resolve()
    if not source.exists():
        print(f"Error: Source directory not found: {source}")
        return 1

    usb = find_usb_drive()
    if not usb:
        usb = find_usb_drive_for_init()
    if not usb:
        print("Error: Could not find USB drive")
        return 1

    repos_dir = usb / REPOS_DIR
    repos_dir.mkdir(exist_ok=True)

    # Create marker file
    marker = usb / MARKER_FILE
    marker.write_text(f"USB Git Sync marker\nSource: {source}\n", encoding="utf-8")
    print(f"Created marker: {marker}")

    repos = get_repos(source)
    if not repos:
        print(f"No git repos found in {source}")
        return 1

    print(f"\nFound {len(repos)} repos in {source}")

    # Check for dirty repos first
    dirty_repos = []
    for repo in repos:
        result = subprocess.run(["git", "status", "--porcelain"],
                               cwd=repo, capture_output=True, text=True)
        if result.stdout.strip():
            rel_path = repo.relative_to(source)
            dirty_repos.append((rel_path, result.stdout.strip()[:100]))

    if dirty_repos:
        print(f"\nWARNING: {len(dirty_repos)} repos have uncommitted changes:")
        for rel_path, changes in dirty_repos[:10]:  # Show first 10
            print(f"  - {rel_path}")
        if len(dirty_repos) > 10:
            print(f"  ... and {len(dirty_repos) - 10} more")
        print()
        response = input("Continue anyway? Only committed changes will sync. (y/n): ").strip().lower()
        if response != "y":
            print("Aborted. Commit or stash changes first.")
            return 1

    print(f"Creating bare repos in {repos_dir}\n")

    for repo in repos:
        # Use relative path from source as name (e.g., Work/foo/bar -> Work__foo__bar)
        rel_path = repo.relative_to(source)
        name = str(rel_path).replace("\\", "/").replace("/", "__")
        bare_path = repos_dir / f"{name}.git"

        print(f"\n[{rel_path}]")

        # Create bare repo if it doesn't exist
        if not bare_path.exists():
            print(f"  Creating bare repo: {bare_path}")
            subprocess.run(["git", "clone", "--bare", str(repo), str(bare_path)],
                          capture_output=True)

        # Add usb remote if not exists
        result = subprocess.run(["git", "remote", "get-url", "usb"],
                               cwd=repo, capture_output=True, text=True)
        if result.returncode != 0:
            # Remote doesn't exist, add it
            bare_url = str(bare_path).replace("\\", "/")
            run_git(["remote", "add", "usb", bare_url], cwd=repo)
        else:
            # Update remote URL in case drive letter changed
            bare_url = str(bare_path).replace("\\", "/")
            run_git(["remote", "set-url", "usb", bare_url], cwd=repo)

        # Push all branches
        run_git(["push", "usb", "--all"], cwd=repo, check=False)
        run_git(["push", "usb", "--tags"], cwd=repo, check=False)

    # Copy this script to USB root for portability
    script_path = Path(__file__).resolve()
    usb_script = usb / script_path.name
    shutil.copy2(script_path, usb_script)
    print(f"\nCopied sync script to: {usb_script}")

    print("\n" + "=" * 50)
    print("Init complete. Safe to eject USB.")
    print("At home, run: python D:/usb-git-sync.py clone")
    print("  (adjust drive letter if different)")
    return 0


def cmd_clone(args):
    """Clone all repos from USB to local machine."""
    usb = find_usb_drive()
    if not usb:
        print("Error: USB drive not found. Is it plugged in?")
        print("Looking for drive with .usb-git-sync marker file.")
        return 1

    repos_dir = usb / REPOS_DIR
    if not repos_dir.exists():
        print(f"Error: Repos directory not found: {repos_dir}")
        return 1

    dest = Path(args.dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    bare_repos = sorted(repos_dir.glob("*.git"))
    print(f"Found {len(bare_repos)} repos on USB")
    print(f"Cloning to {dest}\n")

    for bare in bare_repos:
        # Convert name back to path (e.g., Work__foo__bar.git -> Work/foo/bar)
        name = bare.name[:-4]  # Remove .git suffix
        rel_path = name.replace("__", "/")
        local_path = dest / rel_path

        print(f"\n[{rel_path}]")

        if local_path.exists():
            print(f"  Already exists, skipping clone")
            # Just add/update the usb remote
            bare_url = str(bare).replace("\\", "/")
            result = subprocess.run(["git", "remote", "get-url", "usb"],
                                   cwd=local_path, capture_output=True)
            if result.returncode != 0:
                run_git(["remote", "add", "usb", bare_url], cwd=local_path)
            else:
                run_git(["remote", "set-url", "usb", bare_url], cwd=local_path)
            run_git(["pull", "usb", "main"], cwd=local_path, check=False)
        else:
            # Create parent directories if needed
            local_path.parent.mkdir(parents=True, exist_ok=True)
            bare_url = str(bare).replace("\\", "/")
            run_git(["clone", bare_url, str(local_path)])
            # Add usb remote pointing to the bare repo
            run_git(["remote", "add", "usb", bare_url], cwd=local_path)

    print("\n" + "=" * 50)
    print("Clone complete. You can eject USB if desired.")
    print("When done working, run: python usb-git-sync.py push")
    return 0


def cmd_push(args):
    """Push all local changes to USB."""
    usb = find_usb_drive()
    if not usb:
        print("Error: USB drive not found. Is it plugged in?")
        return 1

    repos_dir = usb / REPOS_DIR
    source = Path(args.source).resolve()

    repos = get_repos(source)
    print(f"Found {len(repos)} repos")

    # Check for dirty repos first
    dirty_repos = []
    for repo in repos:
        result = subprocess.run(["git", "status", "--porcelain"],
                               cwd=repo, capture_output=True, text=True)
        if result.stdout.strip():
            rel_path = repo.relative_to(source)
            dirty_repos.append((rel_path, result.stdout.strip()[:100]))

    if dirty_repos:
        print(f"\nWARNING: {len(dirty_repos)} repos have uncommitted changes:")
        for rel_path, changes in dirty_repos[:10]:  # Show first 10
            print(f"  - {rel_path}")
        if len(dirty_repos) > 10:
            print(f"  ... and {len(dirty_repos) - 10} more")
        print()
        response = input("Continue anyway? Only committed changes will sync. (y/n): ").strip().lower()
        if response != "y":
            print("Aborted. Commit or stash changes first.")
            return 1

    print(f"\nPushing to USB...\n")

    for repo in repos:
        rel_path = repo.relative_to(source)
        name = str(rel_path).replace("\\", "/").replace("/", "__")
        print(f"\n[{rel_path}]")

        # Update remote URL in case drive letter changed
        bare_path = repos_dir / f"{name}.git"
        if bare_path.exists():
            bare_url = str(bare_path).replace("\\", "/")
            run_git(["remote", "set-url", "usb", bare_url], cwd=repo, check=False)

        # Push all branches and tags
        run_git(["push", "usb", "--all"], cwd=repo, check=False)
        run_git(["push", "usb", "--tags"], cwd=repo, check=False)

    print("\n" + "=" * 50)
    print("Push complete. Safe to eject USB.")
    print("Monday at work, run: python usb-git-sync.py pull")
    return 0


def cmd_pull(args):
    """Pull all changes from USB to local repos."""
    usb = find_usb_drive()
    if not usb:
        print("Error: USB drive not found. Is it plugged in?")
        return 1

    repos_dir = usb / REPOS_DIR
    dest = Path(args.dest).resolve()

    repos = get_repos(dest)
    print(f"Pulling {len(repos)} repos from USB\n")

    for repo in repos:
        rel_path = repo.relative_to(dest)
        name = str(rel_path).replace("\\", "/").replace("/", "__")
        print(f"\n[{rel_path}]")

        # Update remote URL in case drive letter changed
        bare_path = repos_dir / f"{name}.git"
        if bare_path.exists():
            bare_url = str(bare_path).replace("\\", "/")
            run_git(["remote", "set-url", "usb", bare_url], cwd=repo, check=False)

        # Get current branch
        result = subprocess.run(["git", "branch", "--show-current"],
                               cwd=repo, capture_output=True, text=True)
        branch = result.stdout.strip() or "main"

        # Pull from usb
        run_git(["pull", "usb", branch], cwd=repo, check=False)

    print("\n" + "=" * 50)
    print("Pull complete.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="USB Git Sync - Portable repo sync via USB drive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  init   Friday at work - Create bare repos on USB, push all
  clone  Friday at home - Clone all repos from USB
  push   Sunday evening - Push all changes to USB
  pull   Monday at work - Pull all changes from USB
        """
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = subparsers.add_parser("init", help="Create bare repos and push")
    p_init.add_argument("--source", default=str(DEFAULT_SOURCE),
                        help=f"Source directory (default: {DEFAULT_SOURCE})")

    # clone
    p_clone = subparsers.add_parser("clone", help="Clone repos from USB")
    p_clone.add_argument("--dest", default=str(DEFAULT_SOURCE),
                         help=f"Destination directory (default: {DEFAULT_SOURCE})")

    # push
    p_push = subparsers.add_parser("push", help="Push changes to USB")
    p_push.add_argument("--source", default=str(DEFAULT_SOURCE),
                        help=f"Source directory (default: {DEFAULT_SOURCE})")

    # pull
    p_pull = subparsers.add_parser("pull", help="Pull changes from USB")
    p_pull.add_argument("--dest", default=str(DEFAULT_SOURCE),
                        help=f"Destination directory (default: {DEFAULT_SOURCE})")

    args = parser.parse_args()

    if args.command == "init":
        return cmd_init(args)
    elif args.command == "clone":
        return cmd_clone(args)
    elif args.command == "push":
        return cmd_push(args)
    elif args.command == "pull":
        return cmd_pull(args)


if __name__ == "__main__":
    sys.exit(main())
