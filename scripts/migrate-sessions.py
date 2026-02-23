"""Migrate Claude Code session history when a workspace moves to a new path.

Claude stores conversation history under ~/.claude/projects/ keyed by the
encoded workspace path (C:\foo\bar -> C--foo-bar). When you move a workspace,
/resume shows no history because the path changed. This script renames the
session directory to match the new path.

Usage:
    python scripts/migrate-sessions.py <old-path> <new-path>
    python scripts/migrate-sessions.py --dry-run <old-path> <new-path>

Examples:
    python scripts/migrate-sessions.py "C:/Users/me/claudes/Work/MyProject" "C:/Users/me/claudes/Github/CC-Optimizer/workspaces/Gitea/MyProject"
"""

import sys
from pathlib import Path


def encode_path(workspace_path):
    """Encode a workspace path the way Claude Code does.

    Replaces backslashes and colons with hyphens.
    C:\\Users\\me\\project -> C--Users-me-project
    """
    # Normalize to absolute path with backslashes (Windows canonical form)
    p = str(Path(workspace_path).resolve())
    # Replace backslashes and colons with hyphens
    encoded = p.replace("\\", "-").replace(":", "-")
    return encoded


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry_run = "--dry-run" in sys.argv

    if len(args) != 2:
        print("Usage: python scripts/migrate-sessions.py [--dry-run] <old-path> <new-path>")
        print()
        print("Renames the session directory under ~/.claude/projects/ so that")
        print("/resume finds your conversation history at the new workspace path.")
        sys.exit(1)

    old_path, new_path = args
    old_encoded = encode_path(old_path)
    new_encoded = encode_path(new_path)

    projects_dir = Path.home() / ".claude" / "projects"

    if not projects_dir.exists():
        print(f"ERROR: {projects_dir} does not exist.")
        sys.exit(1)

    old_dir = projects_dir / old_encoded
    new_dir = projects_dir / new_encoded

    print(f"Old path:    {old_path}")
    print(f"Old encoded: {old_encoded}")
    print(f"New path:    {new_path}")
    print(f"New encoded: {new_encoded}")
    print()

    if not old_dir.exists():
        print(f"ERROR: No session directory found at {old_dir}")
        print()
        # Help debug by listing close matches
        prefix = old_encoded.rsplit("-", 1)[0] if "-" in old_encoded else old_encoded[:20]
        matches = [d.name for d in projects_dir.iterdir() if d.is_dir() and d.name.startswith(prefix)]
        if matches:
            print("Similar directories found:")
            for m in matches:
                print(f"  {m}")
        sys.exit(1)

    if new_dir.exists():
        print(f"WARNING: Target already exists at {new_dir}")
        answer = input("Merge into existing? Sessions from old path will be copied in. [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            sys.exit(0)

        if dry_run:
            print("[DRY RUN] Would merge session files from old into new directory.")
        else:
            # Move individual session subdirs from old into new
            moved = 0
            for item in old_dir.iterdir():
                dest = new_dir / item.name
                if dest.exists():
                    print(f"  Skipping {item.name} (already exists in target)")
                else:
                    item.rename(dest)
                    moved += 1
            print(f"Merged {moved} session(s) into {new_dir.name}")
            # Remove old dir if empty
            remaining = list(old_dir.iterdir())
            if not remaining:
                old_dir.rmdir()
                print(f"Removed empty old directory.")
            else:
                print(f"Old directory still has {len(remaining)} item(s), not removed.")
    else:
        if dry_run:
            print(f"[DRY RUN] Would rename:")
            print(f"  {old_dir}")
            print(f"  -> {new_dir}")
        else:
            old_dir.rename(new_dir)
            print(f"Renamed session directory.")
            print(f"/resume will now find your history at the new workspace path.")


if __name__ == "__main__":
    main()
