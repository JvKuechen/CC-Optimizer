"""Post-clone setup for CC-Optimizer workspace.

Creates WS/ directory for nested workspaces and installs git hooks.
Wiki sync is handled by CI workflows (.github/workflows/wiki-sync.yml
and .gitea/workflows/wiki-sync.yml). Safe to run multiple times --
skips steps that are already done.

Usage: python scripts/setup.py
"""

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / ".git" / "hooks"
CONFIGS_DIR = REPO_ROOT / "configs"
WORKSPACES_DIR = REPO_ROOT / "WS"

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
# Pre-push hook: on public repos, show a diff summary for human review.

REPO_ROOT="$(git rev-parse --show-toplevel)"

# --- Public Repo Push Summary ---
if [ -f "$REPO_ROOT/.public-repo" ]; then
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

exit 0
"""


def run(cmd, cwd=None):
    """Run a command and return stdout. Raises on failure."""
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()


def _install_hook(name, content, version_marker, hooks_dir=None, label="hooks"):
    """Install or update a git hook."""
    target_dir = hooks_dir or HOOKS_DIR
    hook_path = target_dir / name

    if hook_path.exists():
        current = hook_path.read_text(encoding="utf-8")
        if version_marker in current:
            print(f"[{label}] {name} hook is up to date.")
            return
        else:
            print(f"[{label}] Updating {name} hook (old version)...")
    else:
        print(f"[{label}] Installing {name} hook...")

    hook_path.write_text(content, encoding="utf-8", newline="\n")
    print(f"[{label}] {name} hook installed.")


def setup_hooks():
    """Install git hooks if missing or outdated."""
    HOOKS_DIR.mkdir(exist_ok=True)
    _install_hook("pre-commit", PRE_COMMIT_HOOK, "PUBLIC_REPO_VERIFIED")
    _install_hook("pre-push", PRE_PUSH_HOOK, "Public Repo Push Summary")
    _install_hook("commit-msg", COMMIT_MSG_HOOK, "Co-Authored-By")


def _load_user_config():
    """Load user config if it exists, return dict or empty dict."""
    config_path = CONFIGS_DIR / "user-config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_user_config(cfg):
    """Save user config, creating configs/ if needed."""
    CONFIGS_DIR.mkdir(exist_ok=True)
    config_path = CONFIGS_DIR / "user-config.json"
    with open(config_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def setup_workspaces():
    """Create WS/ directory for nested workspace clones."""
    if not WORKSPACES_DIR.exists():
        WORKSPACES_DIR.mkdir()
        print("[workspaces] Created WS/")
    else:
        print("[workspaces] WS/ already exists.")


def setup_long_paths():
    """Ensure Windows long path support is enabled for git and the OS."""
    import platform
    if platform.system() != "Windows":
        print("[longpaths] Not on Windows, skipping.")
        return

    # Git: core.longpaths
    try:
        result = subprocess.run(
            "git config --global core.longpaths",
            capture_output=True, text=True, shell=True,
        )
        if result.stdout.strip().lower() == "true":
            print("[longpaths] git core.longpaths already enabled.")
        else:
            subprocess.run(
                "git config --global core.longpaths true",
                capture_output=True, text=True, shell=True,
            )
            print("[longpaths] Enabled git core.longpaths globally.")
    except Exception as e:
        print(f"[longpaths] WARNING: Could not set git core.longpaths: {e}")

    # Windows registry: LongPathsEnabled
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\FileSystem",
            0, winreg.KEY_READ,
        )
        value, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
        winreg.CloseKey(key)
        if value == 1:
            print("[longpaths] Windows LongPathsEnabled is ON.")
        else:
            print("[longpaths] WARNING: Windows LongPathsEnabled is OFF.")
            print("  Nested workspaces may hit the 260-char path limit.")
            print("  To fix, run as admin: reg add HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f")
    except Exception:
        print("[longpaths] WARNING: Could not check Windows LongPathsEnabled registry key.")
        print("  If you hit path length errors, run as admin:")
        print("  reg add HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f")


def setup_git_identity():
    """Check git user.email is set and linked to a hosting account.

    GitHub noreply emails must include the username prefix to link commits
    to the account. Bare noreply@users.noreply.github.com shows as a
    ghost contributor.
    """
    result = subprocess.run(
        "git config user.email",
        cwd=REPO_ROOT, capture_output=True, text=True, shell=True,
    )
    email = result.stdout.strip()

    if not email:
        # Check global
        result = subprocess.run(
            "git config --global user.email",
            capture_output=True, text=True, shell=True,
        )
        email = result.stdout.strip()

    if not email:
        print("[git-identity] WARNING: No git user.email configured.")
        print("  Commits won't be linked to your account on GitHub/Gitea.")
        print("  Run: git config --global user.email \"you@example.com\"")
        return

    # Detect bare noreply (missing username prefix)
    if email == "noreply@users.noreply.github.com":
        print(f"[git-identity] WARNING: Email is bare noreply without username prefix.")
        print(f"  Current:  {email}")
        print("  GitHub won't link these commits to your account.")
        answer = input("  Enter your GitHub username (or press Enter to skip): ").strip()
        if answer:
            fixed = f"{answer}@users.noreply.github.com"
            subprocess.run(
                f'git config --global user.email "{fixed}"',
                capture_output=True, text=True, shell=True,
            )
            # Also fix repo-level if set
            subprocess.run(
                f'git config user.email "{fixed}"',
                cwd=REPO_ROOT, capture_output=True, text=True, shell=True,
            )
            print(f"[git-identity] Set email to {fixed}")
        else:
            print("[git-identity] Skipped. Fix manually later.")
        return

    print(f"[git-identity] Email: {email}")


def main():
    import sys
    print(f"Setting up CC-Optimizer workspace at {REPO_ROOT}\n")
    setup_git_identity()
    print()
    setup_long_paths()
    print()
    setup_workspaces()
    print()
    setup_hooks()
    print("\nSetup complete.")


if __name__ == "__main__":
    main()
