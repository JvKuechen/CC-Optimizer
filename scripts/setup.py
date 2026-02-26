"""Post-clone setup for CC-Optimizer workspace.

Creates workspaces directory structure, clones the wiki nested repo,
and installs the pre-push hook. Safe to run multiple times -- skips
steps that are already done.

Usage: python scripts/setup.py
"""

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
HOOKS_DIR = REPO_ROOT / ".git" / "hooks"
CONFIGS_DIR = REPO_ROOT / "configs"
WORKSPACES_DIR = REPO_ROOT / "workspaces"
DEFAULT_ORGS = ["Work", "Personal", "Github"]


def _derive_wiki_urls():
    """Derive wiki clone URLs from the main repo's remotes.

    Wiki repos follow the pattern: <repo-url-without-.git>.wiki.git
    Checks all remotes on the main repo and converts each to a wiki URL.
    """
    urls = []
    try:
        result = subprocess.run(
            "git remote", cwd=REPO_ROOT,
            capture_output=True, text=True, shell=True,
        )
        for remote_name in result.stdout.strip().splitlines():
            r = subprocess.run(
                f"git remote get-url {remote_name}",
                cwd=REPO_ROOT, capture_output=True, text=True, shell=True,
            )
            url = r.stdout.strip()
            if url:
                if url.endswith(".git"):
                    urls.append(url[:-4] + ".wiki.git")
                else:
                    urls.append(url + ".wiki.git")
    except Exception:
        pass
    return urls


def _load_wiki_remotes():
    """Load wiki remote config: primary URL, push URLs, and remote name.

    Naming convention (matches dual-remote-push pattern):
      - public:  any push URL points to a public host
      - mirrors: multiple private remotes (bridge pattern)
      - <host>:  single private remote

    Returns dict with keys: name, clone_url, push_urls
    """
    push_urls = []

    # Try user config first
    config_path = CONFIGS_DIR / "user-config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for key in ["wiki_remote_gitea", "wiki_remote_github"]:
            url = cfg.get(key, "")
            if url and "example.com" not in url and "your-" not in url:
                push_urls.append(url)

    # Fallback: derive from main repo remotes
    if not push_urls:
        push_urls = _derive_wiki_urls()

    if not push_urls:
        print("[wiki] WARNING: Could not determine wiki URL.")
        print("       Create configs/user-config.json (see configs/user-config.example.json)")
        return None

    # Determine remote name based on visibility
    is_public = (REPO_ROOT / ".public-repo").exists()
    if is_public:
        name = "public"
    elif len(push_urls) > 1:
        name = "mirrors"
    else:
        # Single remote: name after host
        from urllib.parse import urlparse
        host = urlparse(push_urls[0]).hostname or "origin"
        # Use short name for known hosts
        if "github" in host:
            name = "github"
        elif "gitea" in host or "git." in host:
            name = "gitea"
        else:
            name = host.split(".")[0]

    return {
        "name": name,
        "clone_url": push_urls[0],
        "push_urls": push_urls,
    }


WIKI_REMOTES = _load_wiki_remotes()

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


def run(cmd, cwd=None):
    """Run a command and return stdout. Raises on failure."""
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()


def setup_wiki():
    """Clone wiki if missing, set up remote with dual push URLs."""
    if not WIKI_REMOTES:
        print("[wiki] ERROR: No wiki URL available. Skipping.")
        return

    remote_name = WIKI_REMOTES["name"]
    clone_url = WIKI_REMOTES["clone_url"]
    push_urls = WIKI_REMOTES["push_urls"]

    if (WIKI_DIR / ".git").exists():
        print("[wiki] Already cloned.")
    else:
        print(f"[wiki] Cloning from {clone_url}...")
        run(f'git clone "{clone_url}" "{WIKI_DIR}"')
        print("[wiki] Cloned.")

    # Set up the named remote with dual push URLs
    existing = run("git remote", cwd=WIKI_DIR).splitlines()

    # Remove 'origin' if it was created by git clone and we want a different name
    if "origin" in existing and remote_name != "origin":
        run(f"git remote rename origin {remote_name}", cwd=WIKI_DIR)
        print(f"[wiki] Renamed origin -> {remote_name}")
        existing = [remote_name if r == "origin" else r for r in existing]

    if remote_name not in existing:
        run(
            f'git remote add {remote_name} "{clone_url}"',
            cwd=WIKI_DIR,
        )
        print(f"[wiki] Added remote: {remote_name}")

    # Set up push URLs (first --add --push replaces implicit, so add all)
    if len(push_urls) > 1:
        for url in push_urls:
            run(
                f'git remote set-url --add --push {remote_name} "{url}"',
                cwd=WIKI_DIR,
            )
        print(f"[wiki] Configured {len(push_urls)} push URLs on {remote_name}")

    # Set branch tracking
    branch = run(
        "git symbolic-ref --short HEAD", cwd=WIKI_DIR,
    ) or "master"
    try:
        run(f"git fetch {remote_name}", cwd=WIKI_DIR)
        run(
            f"git branch --set-upstream-to={remote_name}/{branch} {branch}",
            cwd=WIKI_DIR,
        )
    except RuntimeError:
        # Remote may not have this branch yet (fresh wiki)
        pass


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


def setup_wiki_hooks():
    """Install git hooks in the wiki repo."""
    wiki_hooks_dir = WIKI_DIR / ".git" / "hooks"
    if not (WIKI_DIR / ".git").exists():
        print("[wiki-hooks] Wiki not cloned yet, skipping.")
        return
    wiki_hooks_dir.mkdir(exist_ok=True)
    _install_hook(
        "pre-commit", PRE_COMMIT_HOOK, "PUBLIC_REPO_VERIFIED",
        hooks_dir=wiki_hooks_dir, label="wiki-hooks",
    )
    _install_hook(
        "commit-msg", COMMIT_MSG_HOOK, "Co-Authored-By",
        hooks_dir=wiki_hooks_dir, label="wiki-hooks",
    )


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


def _get_workspace_orgs(reconfigure=False):
    """Get org folders from config, or prompt the user interactively."""
    cfg = _load_user_config()

    if "workspace_orgs" in cfg and not reconfigure:
        return cfg["workspace_orgs"]

    existing = cfg.get("workspace_orgs", [])
    if existing:
        print(f"[workspaces] Current org folders: {', '.join(existing)}")
        answer = input("  Enter new comma-separated list (or press Enter to keep): ").strip()
    else:
        print("[workspaces] No workspace_orgs configured.")
        print(f"  Default org folders: {', '.join(DEFAULT_ORGS)}")
        answer = input("  Press Enter to accept defaults, or type comma-separated names: ").strip()

    if answer:
        orgs = [o.strip() for o in answer.split(",") if o.strip()]
    elif existing:
        return existing
    else:
        orgs = list(DEFAULT_ORGS)

    # Save to config so future runs are non-interactive
    cfg["workspace_orgs"] = orgs
    _save_user_config(cfg)
    print("[workspaces] Saved workspace_orgs to configs/user-config.json")

    return orgs


def setup_wiki_public_repo_marker():
    """Create .public-repo marker in the wiki if missing."""
    if not (WIKI_DIR / ".git").exists():
        print("[wiki-marker] Wiki not cloned yet, skipping.")
        return
    marker = WIKI_DIR / ".public-repo"
    if marker.exists():
        print("[wiki-marker] .public-repo marker already exists.")
    else:
        marker.write_text(
            "# Public Repository Marker\n"
            "#\n"
            "# This wiki is published to GitHub. The pre-commit hook blocks\n"
            "# direct git commit. Use PUBLIC_REPO_VERIFIED=1 git commit\n"
            "# after reviewing the diff for sensitive content.\n",
            encoding="utf-8",
            newline="\n",
        )
        print("[wiki-marker] Created .public-repo marker in wiki/")


def setup_workspaces(reconfigure=False):
    """Create workspaces directory structure from user config."""
    orgs = _get_workspace_orgs(reconfigure=reconfigure)

    if not WORKSPACES_DIR.exists():
        WORKSPACES_DIR.mkdir()
        print("[workspaces] Created workspaces/")
    else:
        print("[workspaces] Directory already exists.")

    for org in orgs:
        org_dir = WORKSPACES_DIR / org
        if not org_dir.exists():
            org_dir.mkdir()
            print(f"[workspaces] Created workspaces/{org}/")
        else:
            print(f"[workspaces] workspaces/{org}/ already exists.")


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
    reconfigure = "--reconfigure" in sys.argv

    print(f"Setting up CC-Optimizer workspace at {REPO_ROOT}\n")
    setup_git_identity()
    print()
    setup_long_paths()
    print()
    setup_workspaces(reconfigure=reconfigure)
    print()
    setup_wiki()
    print()
    setup_hooks()
    print()
    setup_wiki_hooks()
    print()
    setup_wiki_public_repo_marker()
    print("\nSetup complete.")


if __name__ == "__main__":
    main()
