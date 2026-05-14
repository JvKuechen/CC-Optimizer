"""Roll out CI-based wiki sync to all workspaces with wiki/ directories.

For each workspace:
1. Add .gitea/workflows/wiki-sync.yml (generic, no edits needed)
2. Remove wiki/.git/ entry from .gitignore
3. Remove post-commit hook (wiki sync to subrepo)
4. Update pre-push hook (strip wiki push section)
5. Delete wiki/.git/ directory

Usage:
    python scripts/rollout-wiki-sync.py              # Preview (dry run)
    python scripts/rollout-wiki-sync.py --apply       # Apply changes
    python scripts/rollout-wiki-sync.py --apply --ws ActiveDirectory  # Single workspace
"""
import argparse
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WS_DIR = REPO_ROOT / "WS"

# The workflow file is generic -- uses github.server_url and github.repository
WIKI_SYNC_WORKFLOW = (
    REPO_ROOT / ".gitea" / "workflows" / "wiki-sync.yml"
).read_text(encoding="utf-8")


def find_workspaces(only=None):
    """Find workspaces with wiki/ directories."""
    results = []
    for d in sorted(WS_DIR.iterdir()):
        if not d.is_dir() or d.name == "desktop.ini":
            continue
        if only and d.name != only:
            continue
        if (d / "wiki").is_dir():
            results.append(d)
    return results


def add_workflow(ws, dry_run):
    """Add .gitea/workflows/wiki-sync.yml."""
    wf_dir = ws / ".gitea" / "workflows"
    wf_path = wf_dir / "wiki-sync.yml"

    if wf_path.exists():
        existing = wf_path.read_text(encoding="utf-8")
        if "Sync wiki" in existing:
            print(f"  [workflow] Already exists, skipping.")
            return False

    if dry_run:
        print(f"  [workflow] Would create .gitea/workflows/wiki-sync.yml")
        return True

    wf_dir.mkdir(parents=True, exist_ok=True)
    wf_path.write_text(WIKI_SYNC_WORKFLOW, encoding="utf-8", newline="\n")
    print(f"  [workflow] Created .gitea/workflows/wiki-sync.yml")
    return True


def update_gitignore(ws, dry_run):
    """Remove wiki/.git/ entry from .gitignore."""
    gi = ws / ".gitignore"
    if not gi.exists():
        return False

    text = gi.read_text(encoding="utf-8")
    if "wiki/.git/" not in text:
        print(f"  [gitignore] No wiki/.git/ entry, skipping.")
        return False

    # Remove the comment + entry
    updated = re.sub(
        r"# Wiki content is tracked; only the wiki subrepo's \.git is ignored\n"
        r"wiki/\.git/\n?",
        "",
        text,
    )
    # Also try without comment
    if updated == text:
        updated = re.sub(r"wiki/\.git/\n?", "", text)

    if updated == text:
        print(f"  [gitignore] Could not remove wiki/.git/ entry.")
        return False

    if dry_run:
        print(f"  [gitignore] Would remove wiki/.git/ entry")
        return True

    gi.write_text(updated, encoding="utf-8", newline="\n")
    print(f"  [gitignore] Removed wiki/.git/ entry")
    return True


def remove_post_commit(ws, dry_run):
    """Delete the post-commit hook."""
    hook = ws / ".git" / "hooks" / "post-commit"
    if not hook.exists():
        print(f"  [post-commit] Not present, skipping.")
        return False

    if dry_run:
        print(f"  [post-commit] Would delete .git/hooks/post-commit")
        return True

    hook.unlink()
    print(f"  [post-commit] Deleted")
    return True


def update_pre_push(ws, dry_run):
    """Strip wiki push section from pre-push hook."""
    hook = ws / ".git" / "hooks" / "pre-push"
    if not hook.exists():
        print(f"  [pre-push] Not present, skipping.")
        return False

    text = hook.read_text(encoding="utf-8")
    if "Wiki push" not in text:
        print(f"  [pre-push] No wiki section, skipping.")
        return False

    # Remove from "# --- Wiki push ---" to the end (before final exit 0)
    updated = re.sub(
        r"\n# --- Wiki push ---.*?(?=exit 0\n)",
        "\n",
        text,
        flags=re.DOTALL,
    )

    # Also update the header comment if it mentions wiki
    updated = re.sub(
        r"# Pre-push hook:\n"
        r"# 1\. If public repo, show a diff summary for human review before pushing\.\n"
        r"# 2\. Push the wiki repo when the main repo is pushed\.",
        "# Pre-push hook: on public repos, show a diff summary for human review.",
        updated,
    )

    # Clean up "# --- Public repo: ..." comment to simpler form
    updated = updated.replace(
        "# --- Public repo: show diff summary for human review ---",
        "# --- Public Repo Push Summary ---",
    )

    # Remove "# Find what's being pushed..." comment
    updated = updated.replace(
        "    # Find what's being pushed vs what the remote already has\n",
        "",
    )

    # Remove "# Always allow the main push to proceed" comment (redundant)
    updated = updated.replace(
        "\n# Always allow the main push to proceed\n",
        "\n",
    )

    if dry_run:
        print(f"  [pre-push] Would strip wiki section")
        return True

    hook.write_text(updated, encoding="utf-8", newline="\n")
    print(f"  [pre-push] Stripped wiki section")
    return True


def _rm_readonly(func, path, exc_info):
    """Error handler for shutil.rmtree: clear read-only and retry."""
    import os
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)


def delete_wiki_git(ws, dry_run):
    """Delete wiki/.git/ directory."""
    wiki_git = ws / "wiki" / ".git"
    if not wiki_git.exists():
        print(f"  [wiki/.git] Not present, skipping.")
        return False

    if dry_run:
        print(f"  [wiki/.git] Would delete wiki/.git/")
        return True

    shutil.rmtree(wiki_git, onerror=_rm_readonly)
    print(f"  [wiki/.git] Deleted")
    return True


def process_workspace(ws, dry_run):
    """Apply all changes to a workspace."""
    mode = "[DRY RUN] " if dry_run else ""
    print(f"\n{mode}{ws.name}")
    print(f"  Path: {ws}")

    changed = False
    changed |= add_workflow(ws, dry_run)
    changed |= update_gitignore(ws, dry_run)
    changed |= remove_post_commit(ws, dry_run)
    changed |= update_pre_push(ws, dry_run)
    changed |= delete_wiki_git(ws, dry_run)

    if not changed:
        print(f"  Nothing to do.")
    return changed


def main():
    parser = argparse.ArgumentParser(
        description="Roll out CI-based wiki sync to workspaces."
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Apply changes (default is dry run)"
    )
    parser.add_argument(
        "--ws", type=str, default=None,
        help="Process only this workspace name"
    )
    args = parser.parse_args()
    dry_run = not args.apply

    workspaces = find_workspaces(only=args.ws)
    if not workspaces:
        print("No workspaces with wiki/ found.")
        return

    print(f"Found {len(workspaces)} workspace(s) with wiki/")
    if dry_run:
        print("DRY RUN -- pass --apply to make changes")

    total_changed = 0
    for ws in workspaces:
        if process_workspace(ws, dry_run):
            total_changed += 1

    print(f"\n{'Would modify' if dry_run else 'Modified'} {total_changed}/{len(workspaces)} workspaces.")
    if not dry_run and total_changed > 0:
        print("\nReminder: commit .gitea/workflows/wiki-sync.yml and .gitignore in each workspace.")
        print("The wiki/.git/ deletion and hook changes are local-only (not committed).")


if __name__ == "__main__":
    main()
