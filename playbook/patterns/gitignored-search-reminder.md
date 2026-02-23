# Gitignored Search Reminder

**Source:** CC-Optimizer workspace -- wiki/ gitignored by parent repo, invisible to Grep

## When

Any workspace with gitignored directories that contain content Claude needs to search (wiki repos, generated docs, nested workspace clones, vendor dirs). Without this, Claude silently gets incomplete results and may write to auto memory instead of the actual docs.

## Problem

Claude Code's Grep tool uses ripgrep, which respects `.gitignore` by default. Gitignored directories are silently skipped. Claude Code also passes `--no-config` to rg, so `RIPGREP_CONFIG_PATH` cannot override this. Explicit `path` targeting into the gitignored dir DOES work -- the problem is Claude doesn't know to do it.

## How

Add a PostToolUse hook on Grep that detects root-level searches and reminds Claude to also search the gitignored directories.

### Hook script (`.claude/hooks/grep-reminder.py`)

```python
"""PostToolUse hook for Grep: remind Claude to search gitignored dirs."""
import json
import sys
from pathlib import Path

GITIGNORED_SEARCH_DIRS = ["wiki"]  # Customize per project

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

    if search_path:
        search_resolved = Path(search_path).resolve()
        for gdir in GITIGNORED_SEARCH_DIRS:
            target = repo_root / gdir
            if target.exists():
                try:
                    search_resolved.relative_to(target)
                    return  # Already searching this dir
                except ValueError:
                    pass
        if search_resolved != repo_root:
            return  # Targeted search, skip reminder

    missing = [d for d in GITIGNORED_SEARCH_DIRS
               if (repo_root / d).exists() and any((repo_root / d).iterdir())]

    if not missing:
        return

    dirs_list = ", ".join(missing)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"Note: {dirs_list}/ is gitignored and was not included "
                f"in this search. If results seem incomplete, re-run Grep "
                f"with an explicit path into {dirs_list}/ to include it."
            ),
        }
    }
    print(json.dumps(output))

if __name__ == "__main__":
    main()
```

### Settings (`.claude/settings.json`)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Grep",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/grep-reminder.py",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

## Rules

- Only fires when Grep searches from the repo root (no path or path == root)
- Does NOT fire when searching inside a gitignored dir (already covered)
- Does NOT fire when searching a specific tracked dir (intentionally scoped)
- Customize `GITIGNORED_SEARCH_DIRS` per project
- Zero token cost -- command hook, no LLM invocation
- Nudges Claude to re-search rather than duplicating the search itself

## Why Not Duplicate the Search

A hook that runs rg itself and injects results would need rg on the system PATH (Claude Code's bundled rg is not accessible to hooks). Using Python file search is possible but fragile. The nudge approach is simpler and lets Claude use the Grep tool properly with an explicit path.
