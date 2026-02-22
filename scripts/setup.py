"""Post-clone setup for ClaudeDocs workspace.

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


def _load_wiki_remotes():
    """Load wiki remotes from user config, falling back to example values."""
    config_path = CONFIGS_DIR / "user-config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        gitea_url = cfg.get("gitea_url", "https://gitea.example.com")
        gitea_org = cfg.get("gitea_org", "ExampleOrg")
        github_user = cfg.get("github_username", "<github-user>")
        wiki_repo = cfg.get("github_wiki_repo", "<repo-name>-wiki")
        return {
            gitea_url.replace("https://", ""): {
                "name": "origin",
                "url": cfg.get(
                    "wiki_remote_gitea",
                    f"{gitea_url}/{gitea_org}/CC-Optimizer.wiki.git",
                ),
            },
            "github.com": {
                "name": "github",
                "url": cfg.get(
                    "wiki_remote_github",
                    f"https://github.com/{github_user}/{wiki_repo}.git",
                ),
            },
        }
    else:
        # Fallback: example values (won't actually clone, but shows expected format)
        return {
            "gitea.example.com": {
                "name": "origin",
                "url": "https://gitea.example.com/ExampleOrg/ClaudeDocs.wiki.git",
            },
            "github.com": {
                "name": "github",
                "url": "https://github.com/your-user/your-repo-wiki.git",
            },
        }


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


def get_main_origin():
    """Get the main repo's origin URL."""
    try:
        return run("git remote get-url origin", cwd=REPO_ROOT)
    except RuntimeError:
        return ""


def detect_wiki_clone_url(origin):
    """Pick the best wiki clone URL based on which remote the main repo uses."""
    for pattern, remote in WIKI_REMOTES.items():
        if pattern in origin:
            return remote["url"]
    # Default to GitHub
    return WIKI_REMOTES["github.com"]["url"]


def setup_wiki():
    """Clone wiki if missing, add all remotes."""
    if (WIKI_DIR / ".git").exists():
        print("[wiki] Already cloned.")
    else:
        origin = get_main_origin()
        clone_url = detect_wiki_clone_url(origin)
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
    print(f"Setting up ClaudeDocs workspace at {REPO_ROOT}\n")
    setup_wiki()
    print()
    setup_hooks()
    print("\nSetup complete.")


if __name__ == "__main__":
    main()
