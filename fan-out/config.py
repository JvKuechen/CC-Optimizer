"""Shared configuration loader for fan-out scripts.

All personal data (paths, usernames, project lists) lives in gitignored
JSON configs. Scripts import from here instead of hardcoding.

Setup:
  1. Copy configs/user-config.example.json -> configs/user-config.json
  2. Copy configs/projects.example.json -> configs/projects.json
  3. Fill in your values
"""

import json
import sys
from pathlib import Path

# Resolve paths relative to the repo root (fan-out/../configs/)
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIGS_DIR = _REPO_ROOT / "configs"


def _load_config(name, example_name):
    """Load a JSON config file, with helpful error if missing."""
    config_path = _CONFIGS_DIR / name
    example_path = _CONFIGS_DIR / example_name

    if not config_path.exists():
        print(f"ERROR: {config_path} not found.", file=sys.stderr)
        print(f"Copy {example_path} to {config_path} and fill in your values.",
              file=sys.stderr)
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_user_config():
    """Load user-specific config (paths, domains, usernames).

    Returns dict with keys: username, claudes_dir, github_username,
    gitea_url, gitea_org, etc.
    """
    return _load_config("user-config.json", "user-config.example.json")


def load_projects_config():
    """Load project classification data (skip lists, work indicators, etc.).

    Returns dict with keys: skip_projects, skip_paths, work_indicators,
    work_repos, rename_map, etc.
    """
    return _load_config("projects.json", "projects.example.json")


def resolve_claudes_dir(user_config=None):
    """Get the claudes directory as a resolved Path.

    Handles ~ expansion and forward-slash normalization.
    """
    if user_config is None:
        user_config = load_user_config()
    raw = user_config.get("claudes_dir", "~/claudes")
    return Path(raw).expanduser().resolve()
