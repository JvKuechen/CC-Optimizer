"""Wiki tracking migration for a workspace.

Converts wiki/ from fully gitignored to tracked content with only
wiki/.git/ ignored. Installs git hooks for auto-sync, fixes
.gitattributes, updates CLAUDE.md, and cleans up stale settings.

Usage:
    python scripts/wiki-migrate.py <workspace-path>
    python scripts/wiki-migrate.py <workspace-path> --dry-run
    python scripts/wiki-migrate.py <workspace-path> --github
    python scripts/wiki-migrate.py <workspace-path> --skip-renormalize
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Hook content (canonical source: CC-Optimizer scripts/setup.py)
# ---------------------------------------------------------------------------

PRE_COMMIT_HOOK = r"""#!/bin/bash
# pre-commit hook: block commits on public repos unless verified.
#
# When .public-repo exists at the repo root, direct `git commit` is blocked.
# Use scripts/verified-commit.sh or PUBLIC_REPO_VERIFIED=1 to bypass.

REPO_ROOT="$(git rev-parse --show-toplevel)"

if [ -f "$REPO_ROOT/.public-repo" ] && [ "$PUBLIC_REPO_VERIFIED" != "1" ]; then
    echo ""
    echo "[Public Repo Lock] Commit blocked."
    echo ""
    echo "This repo has public remotes. Before committing, verify the staged"
    echo "diff contains only generalized information (no hostnames, credentials,"
    echo "usernames, IPs, or environment-specific details)."
    echo ""
    echo "Review the diff:"
    echo "  git diff --cached"
    echo ""
    if [ -f "$REPO_ROOT/scripts/verified-commit.sh" ]; then
        echo "Then commit using:"
        echo "  scripts/verified-commit.sh -m \"your message\""
    else
        echo "Then commit using:"
        echo "  PUBLIC_REPO_VERIFIED=1 git commit -m \"your message\""
    fi
    echo ""
    exit 1
fi

exit 0
"""

COMMIT_MSG_HOOK = r"""#!/bin/bash
# commit-msg hook: strip Co-Authored-By lines added by Claude Code.
# GitHub parses these into ghost author avatars with broken names.
# The commit is still made by whoever is in git config user.name/email.

sed -i '/^Co-Authored-By:/d' "$1"
sed -i '/^[[:space:]]*$/N;/^\n$/d' "$1"
"""

PRE_PUSH_HOOK = r"""#!/bin/bash
# Pre-push hook:
# 1. If public repo, show a diff summary for human review before pushing.
# 2. Push the wiki repo when the main repo is pushed.

REPO_ROOT="$(git rev-parse --show-toplevel)"

# --- Public repo: show diff summary for human review ---
if [ -f "$REPO_ROOT/.public-repo" ]; then
    # Find what's being pushed vs what the remote already has
    REMOTE="$1"
    REMOTE_REF=$(git rev-parse "$REMOTE/$(git symbolic-ref --short HEAD)" 2>/dev/null)

    if [ -n "$REMOTE_REF" ]; then
        COMMIT_COUNT=$(git rev-list --count "$REMOTE_REF..HEAD" 2>/dev/null)
        if [ "$COMMIT_COUNT" -gt 0 ]; then
            echo ""
            echo "=== Public Repo Push Summary ==="
            echo "Pushing $COMMIT_COUNT commit(s) to $REMOTE:"
            echo ""
            git log --oneline "$REMOTE_REF..HEAD"
            echo ""
            echo "Files changed:"
            git diff --stat "$REMOTE_REF..HEAD"
            echo ""
            echo "Review the full diff with: git diff $REMOTE_REF..HEAD"
            echo "================================"
            echo ""
        fi
    fi
fi

# --- Wiki push ---
WIKI_DIR="$REPO_ROOT/wiki"

if [ -d "$WIKI_DIR/.git" ]; then
    echo "Pre-push: pushing wiki repo..."
    cd "$WIKI_DIR"

    if git rev-parse --verify HEAD > /dev/null 2>&1; then
        for REMOTE in $(git remote); do
            BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "master")
            git push "$REMOTE" "$BRANCH" 2>&1
            RESULT=$?
            if [ $RESULT -ne 0 ]; then
                echo "WARNING: Wiki push to $REMOTE failed (exit $RESULT). Main repo push continues."
            else
                echo "Pre-push: wiki pushed to $REMOTE."
            fi
        done
    else
        echo "Pre-push: wiki has no commits, skipping."
    fi
else
    echo "Pre-push: no wiki directory found, skipping."
fi

# Always allow the main push to proceed
exit 0
"""

POST_COMMIT_HOOK = r"""#!/bin/bash
# post-commit hook: sync wiki/ changes to the wiki subrepo.
#
# After a main repo commit that touches wiki/ files, this hook
# auto-commits those changes into the wiki's own git repo using
# the main repo's commit subject as the wiki commit message.
#
# Requires wiki/.git to exist (run scripts/setup.py after clone).
# The wiki pre-commit hook (.public-repo lock) is bypassed via
# PUBLIC_REPO_VERIFIED=1 since the content was already reviewed
# when committed to the main repo.

REPO_ROOT="$(git rev-parse --show-toplevel)"
WIKI_DIR="$REPO_ROOT/wiki"

# Skip if wiki subrepo not initialized
if [ ! -d "$WIKI_DIR/.git" ]; then
    exit 0
fi

# Check if this commit touched any wiki/ files
CHANGED=$(git diff-tree --no-commit-id --name-only -r HEAD -- wiki/)
if [ -z "$CHANGED" ]; then
    exit 0
fi

cd "$WIKI_DIR"
SUBJECT=$(git -C "$REPO_ROOT" log -1 --format="%s")
git add -A

if ! git diff --cached --quiet; then
    export PUBLIC_REPO_VERIFIED=1
    git commit -m "$SUBJECT" > /dev/null 2>&1
fi

exit 0
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(cmd, cwd=None):
    """Run a shell command, print warnings on failure, return result."""
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, shell=True
    )
    if result.returncode != 0 and result.stderr.strip():
        print(f"  WARN: {cmd}")
        print(f"    {result.stderr.strip()}")
    return result


def is_dirty(cwd):
    """Check if a git working tree has uncommitted changes."""
    r = subprocess.run(
        "git status --porcelain", cwd=cwd,
        capture_output=True, text=True, shell=True,
    )
    return bool(r.stdout.strip())


# ---------------------------------------------------------------------------
# Migration steps
# ---------------------------------------------------------------------------


def step_commit_dirty_wiki(wiki_dir, dry_run=False):
    """Step 1: Commit any dirty wiki files before migration."""
    print("[1/8] Checking wiki for uncommitted changes...")
    if not is_dirty(wiki_dir):
        print("  Wiki is clean.")
        return

    r = subprocess.run(
        "git status --short", cwd=wiki_dir,
        capture_output=True, text=True, shell=True,
    )
    dirty_files = r.stdout.strip().splitlines()
    print(f"  Found {len(dirty_files)} dirty file(s):")
    for f in dirty_files[:5]:
        print(f"    {f}")
    if len(dirty_files) > 5:
        print(f"    ... and {len(dirty_files) - 5} more")

    if dry_run:
        print("  [DRY RUN] Would commit dirty wiki files.")
        return

    run("git add -A", cwd=wiki_dir)
    run('git commit -m "Pre-migration sync"', cwd=wiki_dir)
    print("  Committed.")


def step_update_gitignore(ws, dry_run=False):
    """Step 2: Change wiki/ to wiki/.git/ in .gitignore."""
    print("[2/8] Updating .gitignore...")
    gitignore = ws / ".gitignore"

    if not gitignore.exists():
        print("  No .gitignore found, skipping.")
        return

    text = gitignore.read_text(encoding="utf-8")

    if "wiki/.git/" in text:
        print("  Already has wiki/.git/ entry.")
        return

    # Try the exact pattern first, then a looser match
    old = "# Wiki (separate git repo)\nwiki/"
    new = "# Wiki content is tracked; only the wiki subrepo's .git is ignored\nwiki/.git/"

    if old in text:
        updated = text.replace(old, new)
    else:
        # Looser: just replace the wiki/ line
        updated = re.sub(
            r"^(#.*wiki.*\n)?wiki/\s*$",
            "# Wiki content is tracked; only the wiki subrepo's .git is ignored\nwiki/.git/",
            text,
            count=1,
            flags=re.MULTILINE,
        )

    if updated == text:
        print("  WARN: Could not find wiki/ entry to replace.")
        return

    if dry_run:
        print("  [DRY RUN] Would change wiki/ -> wiki/.git/")
        return

    gitignore.write_text(updated, encoding="utf-8", newline="\n")
    print("  Updated: wiki/ -> wiki/.git/")


def step_track_wiki(ws, wiki_dir, dry_run=False):
    """Step 3: Track wiki files (gitlink workaround)."""
    print("[3/8] Tracking wiki content in main repo...")
    git_dir = wiki_dir / ".git"
    git_bak = wiki_dir / ".git.bak"

    if dry_run:
        # Count files that would be added
        count = sum(1 for _ in wiki_dir.glob("*.md"))
        print(f"  [DRY RUN] Would track ~{count} wiki files (gitlink workaround).")
        return

    # Force-remove any prior gitlink or cached entry
    run("git rm --cached -f wiki", cwd=ws)

    # Temporarily hide wiki/.git so git sees individual files
    git_dir.rename(git_bak)
    try:
        run("git add wiki/", cwd=ws)
    finally:
        git_bak.rename(git_dir)

    # Count staged wiki files
    result = subprocess.run(
        "git diff --cached --name-only", cwd=ws,
        capture_output=True, text=True, shell=True,
    )
    wiki_files = [f for f in result.stdout.strip().splitlines()
                  if f.startswith("wiki/")]
    print(f"  Staged {len(wiki_files)} wiki files.")


def step_fix_gitattributes(ws, dry_run=False, skip=False):
    """Step 4: Add * text=auto eol=lf baseline if missing."""
    print("[4/8] Checking .gitattributes...")

    if skip:
        print("  Skipped (--skip-renormalize).")
        return

    ga_path = ws / ".gitattributes"

    if ga_path.exists():
        text = ga_path.read_text(encoding="utf-8")
        if "* text=auto" in text:
            print("  Already has baseline LF rule.")
            return
        updated = "* text=auto eol=lf\n" + text
    else:
        updated = "* text=auto eol=lf\n"

    if dry_run:
        print("  [DRY RUN] Would prepend '* text=auto eol=lf' and renormalize.")
        return

    ga_path.write_text(updated, encoding="utf-8", newline="\n")
    print("  Added '* text=auto eol=lf' baseline.")

    print("  Running git add --renormalize ...")
    r = run("git add --renormalize .", cwd=ws)
    run("git add .gitattributes", cwd=ws)

    # Count renormalized files
    result = subprocess.run(
        "git diff --cached --name-only", cwd=ws,
        capture_output=True, text=True, shell=True,
    )
    changed = result.stdout.strip().splitlines()
    # Exclude wiki/ and .gitattributes from count (already counted)
    renorm = [f for f in changed
              if not f.startswith("wiki/") and f != ".gitattributes"]
    if renorm:
        print(f"  Renormalized {len(renorm)} files (CRLF -> LF).")


def step_update_claude_md(ws, dry_run=False):
    """Step 5: Add wiki tracking note to CLAUDE.md."""
    print("[5/8] Updating CLAUDE.md...")
    claude_md = ws / "CLAUDE.md"

    if not claude_md.exists():
        print("  No CLAUDE.md found, skipping.")
        return

    text = claude_md.read_text(encoding="utf-8")

    # Check if already updated
    if "wiki content is tracked" in text.lower() or "searchable with grep" in text.lower():
        print("  Already has wiki tracking note.")
        return

    # Find a wiki link line and replace/augment it
    # Pattern: "- See the [wiki](URL) ..." or similar
    wiki_link_pattern = re.compile(
        r"^(- .*\[wiki\]\(https?://[^)]+\).*?)$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = wiki_link_pattern.search(text)

    if match:
        # Extract the URL from the existing link
        url_match = re.search(r"\(https?://[^)]+\)", match.group(1))
        url = url_match.group(0) if url_match else ""
        replacement = (
            f"- Wiki content is tracked in `wiki/` and searchable with Grep. "
            f"Auto-syncs via git hooks (post-commit + pre-push). "
            f"See the [online wiki]{url} for rendered view."
        )
        updated = text[:match.start()] + replacement + text[match.end():]
    else:
        # No wiki link found -- add a note near the top
        print("  No wiki link found in CLAUDE.md, skipping auto-update.")
        print("  Add manually: 'Wiki content is tracked in wiki/ and searchable with Grep.'")
        return

    if dry_run:
        print("  [DRY RUN] Would update wiki reference line in CLAUDE.md.")
        return

    claude_md.write_text(updated, encoding="utf-8", newline="\n")
    run("git add CLAUDE.md", cwd=ws)
    print("  Updated wiki reference.")


def step_install_hooks(ws, wiki_dir, dry_run=False):
    """Step 6: Install git hooks for main repo and wiki."""
    print("[6/8] Installing git hooks...")

    hooks_dir = ws / ".git" / "hooks"
    wiki_hooks_dir = wiki_dir / ".git" / "hooks"

    hooks = {
        "pre-commit": PRE_COMMIT_HOOK,
        "commit-msg": COMMIT_MSG_HOOK,
        "pre-push": PRE_PUSH_HOOK,
        "post-commit": POST_COMMIT_HOOK,
    }
    wiki_hooks = ["pre-commit", "commit-msg"]

    if dry_run:
        print(f"  [DRY RUN] Would install 4 hooks in .git/hooks/")
        print(f"  [DRY RUN] Would install 2 hooks in wiki/.git/hooks/")
        return

    hooks_dir.mkdir(exist_ok=True)
    for name, content in hooks.items():
        (hooks_dir / name).write_text(content, encoding="utf-8", newline="\n")
        print(f"  .git/hooks/{name}")

    wiki_hooks_dir.mkdir(exist_ok=True)
    for name in wiki_hooks:
        (wiki_hooks_dir / name).write_text(
            hooks[name], encoding="utf-8", newline="\n"
        )
        print(f"  wiki/.git/hooks/{name}")


def step_cleanup_settings_local(ws, dry_run=False):
    """Step 7: Delete stale settings.local.json if present."""
    print("[7/8] Checking for stale settings.local.json...")
    local_settings = ws / ".claude" / "settings.local.json"

    if not local_settings.exists():
        print("  None found.")
        return

    if dry_run:
        print("  [DRY RUN] Would delete .claude/settings.local.json")
        return

    local_settings.unlink()
    print("  Deleted (stale auto-allow entries from previous path).")


def step_switch_wiki_branch(wiki_dir, github=False, dry_run=False):
    """Switch wiki to master branch if --github flag is set."""
    if not github:
        return

    print("  Switching wiki to master branch (GitHub requirement)...")
    if dry_run:
        print("  [DRY RUN] Would checkout master in wiki subrepo.")
        return

    # Check current branch
    r = subprocess.run(
        "git symbolic-ref --short HEAD", cwd=wiki_dir,
        capture_output=True, text=True, shell=True,
    )
    current = r.stdout.strip()

    if current == "master":
        print("  Already on master.")
        return

    # Try checkout master, create if needed
    r = run("git checkout master", cwd=wiki_dir)
    if r.returncode != 0:
        run("git checkout -b master", cwd=wiki_dir)
    print(f"  Switched from {current} to master.")


def step_commit(ws, dry_run=False):
    """Step 8: Commit all migration changes."""
    print("[8/8] Committing migration...")

    if dry_run:
        print("  [DRY RUN] Would commit all staged changes.")
        return

    run("git add .gitignore", cwd=ws)

    result = subprocess.run(
        'git commit -m "Wiki tracking migration: track content, install hooks, fix line endings"',
        cwd=ws, capture_output=True, text=True, shell=True,
    )
    if result.returncode == 0:
        lines = result.stdout.strip().splitlines()
        print(f"  {lines[0] if lines else 'Committed'}")
    else:
        stderr = result.stderr.strip()
        if "nothing to commit" in stderr or "nothing to commit" in result.stdout:
            print("  Nothing to commit (already up to date).")
        else:
            print(f"  Commit stderr: {stderr}")
            print(f"  Commit stdout: {result.stdout.strip()}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Wiki tracking migration for a workspace."
    )
    parser.add_argument(
        "workspace", help="Path to the workspace to migrate"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without modifying anything"
    )
    parser.add_argument(
        "--github", action="store_true",
        help="Switch wiki to master branch (GitHub wiki requirement)"
    )
    parser.add_argument(
        "--skip-renormalize", action="store_true",
        help="Skip .gitattributes fix and line ending renormalization"
    )
    args = parser.parse_args()

    ws = Path(args.workspace).resolve()
    wiki_dir = ws / "wiki"

    # Validate
    if not ws.exists():
        print(f"ERROR: Workspace not found: {ws}")
        sys.exit(1)
    if not wiki_dir.exists():
        print(f"ERROR: No wiki/ directory at {ws}")
        sys.exit(1)
    if not (wiki_dir / ".git").exists():
        print(f"ERROR: No wiki/.git at {ws} (wiki subrepo not initialized)")
        sys.exit(1)

    mode = "[DRY RUN] " if args.dry_run else ""
    print(f"{mode}Wiki tracking migration for: {ws}\n")

    step_commit_dirty_wiki(wiki_dir, dry_run=args.dry_run)
    step_update_gitignore(ws, dry_run=args.dry_run)
    step_track_wiki(ws, wiki_dir, dry_run=args.dry_run)
    step_fix_gitattributes(ws, dry_run=args.dry_run, skip=args.skip_renormalize)
    step_update_claude_md(ws, dry_run=args.dry_run)
    step_install_hooks(ws, wiki_dir, dry_run=args.dry_run)
    step_switch_wiki_branch(wiki_dir, github=args.github, dry_run=args.dry_run)
    step_cleanup_settings_local(ws, dry_run=args.dry_run)
    step_commit(ws, dry_run=args.dry_run)

    print(f"\n{mode}Done!")


if __name__ == "__main__":
    main()
