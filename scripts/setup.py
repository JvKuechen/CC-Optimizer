"""Post-clone setup for CC-Optimizer workspace.

Clones the wiki nested repo and installs the pre-push hook.
Safe to run multiple times -- skips steps that are already done.

Usage: python scripts/setup.py
"""

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
HOOKS_DIR = REPO_ROOT / ".git" / "hooks"
CONFIGS_DIR = REPO_ROOT / "configs"


def _derive_wiki_url_from_origin():
    """Derive the wiki clone URL from the main repo's origin.

    GitHub wiki repos follow the pattern: <repo-url-without-.git>.wiki.git
    For example:
        https://github.com/User/Repo.git -> https://github.com/User/Repo.wiki.git
        git@github.com:User/Repo.git     -> git@github.com:User/Repo.wiki.git
    """
    try:
        result = subprocess.run(
            "git remote get-url origin",
            cwd=REPO_ROOT, capture_output=True, text=True, shell=True,
        )
        origin = result.stdout.strip()
    except Exception:
        origin = ""

    if not origin:
        return None

    # Strip trailing .git if present, append .wiki.git
    if origin.endswith(".git"):
        return origin[:-4] + ".wiki.git"
    return origin + ".wiki.git"


def _load_wiki_remotes():
    """Load wiki remotes from user config, or auto-derive from origin."""
    config_path = CONFIGS_DIR / "user-config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        remotes = {}
        # Add configured remotes (skip entries with placeholder values)
        for key, default_name in [
            ("wiki_remote_gitea", "gitea"),
            ("wiki_remote_github", "github"),
        ]:
            url = cfg.get(key, "")
            if url and "example.com" not in url and "your-" not in url:
                remotes[default_name] = {"name": default_name, "url": url}
        if remotes:
            # Use the first configured remote as "origin"
            first = next(iter(remotes.values()))
            first["name"] = "origin"
            return remotes

    # No config or no valid remotes -- derive from main repo's origin
    wiki_url = _derive_wiki_url_from_origin()
    if wiki_url:
        return {
            "auto": {"name": "origin", "url": wiki_url},
        }

    print("[wiki] WARNING: Could not determine wiki URL.")
    print("       Create configs/user-config.json (see configs/user-config.example.json)")
    return {}


WIKI_REMOTES = _load_wiki_remotes()

PRE_PUSH_HOOK = r"""#!/bin/bash
# Pre-push hook: also push the wiki repo when the main repo is pushed.
# The wiki lives in wiki/ as a separate git repo (not a submodule).
# Pushes to ALL wiki remotes (origin, github, etc.) so they stay in sync.

WIKI_DIR="$(git rev-parse --show-toplevel)/wiki"

if [ -d "$WIKI_DIR/.git" ]; then
    echo "Pre-push: pushing wiki repo..."
    cd "$WIKI_DIR"

    if git rev-parse --verify HEAD > /dev/null 2>&1; then
        for REMOTE in $(git remote); do
            git push "$REMOTE" main 2>&1
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


def detect_wiki_clone_url():
    """Pick the wiki clone URL from configured remotes."""
    if not WIKI_REMOTES:
        return None
    # Use the first (or only) remote's URL
    return next(iter(WIKI_REMOTES.values()))["url"]


def setup_wiki():
    """Clone wiki if missing, add all remotes."""
    if (WIKI_DIR / ".git").exists():
        print("[wiki] Already cloned.")
    else:
        clone_url = detect_wiki_clone_url()
        if not clone_url:
            print("[wiki] ERROR: No wiki URL available. Skipping clone.")
            return
        print(f"[wiki] Cloning from {clone_url}...")
        run(f'git clone "{clone_url}" "{WIKI_DIR}"')
        print("[wiki] Cloned.")

    # Ensure all remotes exist
    existing = run("git remote", cwd=WIKI_DIR).splitlines()
    for remote in WIKI_REMOTES.values():
        if remote["name"] not in existing:
            print(f"[wiki] Adding remote: {remote['name']} -> {remote['url']}")
            run(
                f"git remote add {remote['name']} \"{remote['url']}\"",
                cwd=WIKI_DIR,
            )
        else:
            print(f"[wiki] Remote {remote['name']} already exists.")


def setup_hooks():
    """Install the pre-push hook if missing or outdated."""
    hook_path = HOOKS_DIR / "pre-push"

    if hook_path.exists():
        current = hook_path.read_text(encoding="utf-8")
        if "for REMOTE in" in current:
            print("[hooks] Pre-push hook is up to date.")
            return
        else:
            print("[hooks] Updating pre-push hook (old version)...")
    else:
        print("[hooks] Installing pre-push hook...")

    hook_path.write_text(PRE_PUSH_HOOK, encoding="utf-8", newline="\n")
    print("[hooks] Pre-push hook installed.")


def main():
    print(f"Setting up CC-Optimizer workspace at {REPO_ROOT}\n")
    setup_wiki()
    print()
    setup_hooks()
    print("\nSetup complete.")


if __name__ == "__main__":
    main()
