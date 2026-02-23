"""Migrate Claude Code session history when a workspace moves to a new path.

Claude stores conversation history under ~/.claude/projects/ keyed by the
encoded workspace path (C:\\foo\\bar -> C--foo-bar). When you move a workspace,
/resume shows no history because the path changed. This script renames the
session directory to match the new path.

Usage:
    # Single workspace
    python scripts/migrate-sessions.py <old-path> <new-path>

    # Parent move (migrates parent + all nested workspaces at once)
    python scripts/migrate-sessions.py --parent <old-parent> <new-parent>

    # Dry run (preview only)
    python scripts/migrate-sessions.py --dry-run --parent <old-parent> <new-parent>

Examples:
    # Move one project
    python scripts/migrate-sessions.py "C:/old/MyProject" "C:/new/MyProject"

    # Move CC-Optimizer and all nested workspaces in one command
    python scripts/migrate-sessions.py --parent "C:/Users/me/claudes/Github/CC-Optimizer" "C:/Users/me/CC-Optimizer"
"""

import re
import sys
from pathlib import Path


def encode_path(workspace_path):
    """Encode a workspace path the way Claude Code does.

    All non-alphanumeric characters except hyphens become hyphens.
    C:\\Users\\me\\my_project -> C--Users-me-my-project
    Dots, underscores, spaces, colons, backslashes all become hyphens.
    """
    # Normalize to absolute path with backslashes (Windows canonical form)
    p = str(Path(workspace_path).resolve())
    # Replace any character that is not alphanumeric or hyphen
    encoded = re.sub(r"[^a-zA-Z0-9-]", "-", p)
    return encoded


def migrate_single(old_path, new_path, projects_dir, dry_run):
    """Migrate a single workspace's session directory."""
    old_encoded = encode_path(old_path)
    new_encoded = encode_path(new_path)

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
        prefix = old_encoded.rsplit("-", 1)[0] if "-" in old_encoded else old_encoded[:20]
        matches = [d.name for d in projects_dir.iterdir() if d.is_dir() and d.name.startswith(prefix)]
        if matches:
            print("Similar directories found:")
            for m in matches:
                print(f"  {m}")
        return False

    if new_dir.exists():
        if dry_run:
            print(f"[DRY RUN] Would merge session files from old into new directory.")
            return True

        print(f"WARNING: Target already exists at {new_dir}")
        answer = input("Merge into existing? Sessions from old path will be copied in. [y/N] ").strip().lower()
        if answer != "y":
            print("Skipped.")
            return False

        moved = 0
        for item in old_dir.iterdir():
            dest = new_dir / item.name
            if dest.exists():
                print(f"  Skipping {item.name} (already exists in target)")
            else:
                item.rename(dest)
                moved += 1
        print(f"Merged {moved} session(s) into {new_dir.name}")
        remaining = list(old_dir.iterdir())
        if not remaining:
            old_dir.rmdir()
            print(f"Removed empty old directory.")
        else:
            print(f"Old directory still has {len(remaining)} item(s), not removed.")
    else:
        if dry_run:
            print(f"[DRY RUN] Would rename:")
            print(f"  {old_dir.name}")
            print(f"  -> {new_dir.name}")
        else:
            old_dir.rename(new_dir)
            print(f"Renamed session directory.")

    return True


def migrate_parent(old_parent, new_parent, projects_dir, dry_run):
    """Migrate all session directories under an old parent path prefix.

    Finds every session dir whose encoded name starts with the old parent's
    encoding, then replaces that prefix with the new parent's encoding.
    Handles the parent workspace + all nested workspaces in one pass.
    """
    old_prefix = encode_path(old_parent)
    new_prefix = encode_path(new_parent)

    print(f"Parent move: {old_parent}")
    print(f"         -> {new_parent}")
    print(f"Old prefix:  {old_prefix}")
    print(f"New prefix:  {new_prefix}")
    print()

    # Find all matching session directories
    matches = sorted(
        d for d in projects_dir.iterdir()
        if d.is_dir() and d.name.startswith(old_prefix)
    )

    if not matches:
        print("No session directories found matching the old parent path.")
        print()
        # Show close matches for debugging
        short = old_prefix[:30]
        close = [d.name for d in projects_dir.iterdir() if d.is_dir() and d.name.startswith(short)]
        if close:
            print(f"Directories starting with '{short}':")
            for c in close:
                print(f"  {c}")
        return

    print(f"Found {len(matches)} session directory(ies) to migrate:")
    print()

    migrated = 0
    for old_dir in matches:
        # Replace old prefix with new prefix, keep the suffix (nested path)
        suffix = old_dir.name[len(old_prefix):]
        new_name = new_prefix + suffix
        new_dir = projects_dir / new_name

        print(f"  {old_dir.name}")
        print(f"  -> {new_name}")

        if new_dir.exists():
            if dry_run:
                print(f"  [DRY RUN] Target exists, would merge")
            else:
                # Merge: move session files from old into new
                moved = 0
                for item in old_dir.iterdir():
                    dest = new_dir / item.name
                    if not dest.exists():
                        item.rename(dest)
                        moved += 1
                remaining = list(old_dir.iterdir())
                if not remaining:
                    old_dir.rmdir()
                print(f"  Merged ({moved} sessions moved)")
        else:
            if dry_run:
                print(f"  [DRY RUN] Would rename")
            else:
                old_dir.rename(new_dir)
                print(f"  Done")

        migrated += 1
        print()

    label = "would migrate" if dry_run else "migrated"
    print(f"{migrated} session directory(ies) {label}.")


def main():
    flags = {"--dry-run", "--parent"}
    args = [a for a in sys.argv[1:] if a not in flags]
    dry_run = "--dry-run" in sys.argv
    parent_mode = "--parent" in sys.argv

    if len(args) != 2:
        print("Usage: python scripts/migrate-sessions.py [--dry-run] [--parent] <old-path> <new-path>")
        print()
        print("Renames session directories under ~/.claude/projects/ so that")
        print("/resume finds your conversation history at the new workspace path.")
        print()
        print("Options:")
        print("  --dry-run  Preview changes without renaming anything")
        print("  --parent   Migrate all session dirs under old-path prefix (batch mode)")
        sys.exit(1)

    old_path, new_path = args
    projects_dir = Path.home() / ".claude" / "projects"

    if not projects_dir.exists():
        print(f"ERROR: {projects_dir} does not exist.")
        sys.exit(1)

    if parent_mode:
        migrate_parent(old_path, new_path, projects_dir, dry_run)
    else:
        success = migrate_single(old_path, new_path, projects_dir, dry_run)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
