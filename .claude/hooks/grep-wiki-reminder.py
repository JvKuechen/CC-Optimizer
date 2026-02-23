"""PostToolUse hook for Grep: remind Claude to also search gitignored dirs.

When Grep runs at the repo root (or without an explicit path), gitignored
directories like wiki/ are silently skipped. This hook detects that case
and injects a reminder into Claude's context to search wiki/ separately.
"""
import json
import sys
from pathlib import Path

# Gitignored directories that should be searchable.
# Add paths relative to repo root.
GITIGNORED_SEARCH_DIRS = ["wiki"]


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return

    tool_input = input_data.get("tool_input", {})
    search_path = tool_input.get("path", "")
    cwd = input_data.get("cwd", "")

    if not cwd:
        return

    repo_root = Path(cwd).resolve()

    # If an explicit path was given, check if it already targets
    # one of the gitignored dirs -- if so, no reminder needed.
    if search_path:
        search_resolved = Path(search_path).resolve()
        for gdir in GITIGNORED_SEARCH_DIRS:
            target = repo_root / gdir
            if target.exists():
                try:
                    search_resolved.relative_to(target)
                    # Already searching inside this gitignored dir
                    return
                except ValueError:
                    pass
        # Explicit path that isn't the repo root -- probably targeted,
        # skip the reminder to avoid noise.
        if search_resolved != repo_root:
            return

    # Search was at repo root (no path or path == root).
    # Check which gitignored dirs exist and have content.
    missing_dirs = []
    for gdir in GITIGNORED_SEARCH_DIRS:
        target = repo_root / gdir
        if target.exists() and any(target.iterdir()):
            missing_dirs.append(gdir)

    if not missing_dirs:
        return

    dirs_list = ", ".join(missing_dirs)
    reminder = (
        f"Note: {dirs_list}/ is gitignored and was not included in this search. "
        f"If results seem incomplete, re-run Grep with an explicit path "
        f"into {dirs_list}/ to include it."
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": reminder,
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
