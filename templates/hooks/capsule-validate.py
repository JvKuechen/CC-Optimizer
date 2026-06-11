#!/usr/bin/env python3
"""PostToolUse capsule.toml validator -- the deterministic guard.

Fires after Write/Edit. If the edited file is capsule.toml, it parses the
result and checks the schema; on any failure it exits 2 with a message, which
Claude Code feeds back to the model so the bad edit is corrected immediately.
This is what makes "schema enforced" real instead of advisory: a sloppy edit
(including a stray sed that breaks the TOML) fails LOUD and recoverable rather
than silently corrupting the live state.

Wire it in .claude/settings.json as a PostToolUse hook matching Write|Edit:

  {"hooks": {"PostToolUse": [
    {"matcher": "Write|Edit",
     "hooks": [{"type": "command",
                "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/capsule-validate.py\""}]}
  ]}}

Schema (kept in lockstep with handoff-capsule.py):
  required non-empty strings: role, current_goal, current_state, next_safe_action
  optional lists of strings:  holds_and_gates, open_followons
  optional:                   schema_version (int), updated (str), thread (str),
                              active_wave (str)
"""
import json
import os
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    tomllib = None

REQUIRED = ("role", "current_goal", "current_state", "next_safe_action")
LIST_KEYS = ("holds_and_gates", "open_followons")


def schema_errors(data):
    errs = []
    for key in REQUIRED:
        val = data.get(key)
        if val is None:
            errs.append("missing required key '%s'" % key)
        elif not isinstance(val, str) or not val.strip():
            errs.append("key '%s' must be a non-empty string" % key)
    for key in LIST_KEYS:
        if key in data and not (
            isinstance(data[key], list)
            and all(isinstance(x, str) for x in data[key])
        ):
            errs.append("key '%s' must be a list of strings" % key)
    return errs


def is_capsule(path):
    if path is None:
        return False
    override = os.environ.get("CLAUDE_CAPSULE_FILE")
    name = Path(path).name
    if override:
        return name == Path(override).name
    return name == "capsule.toml"


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not is_capsule(file_path):
        sys.exit(0)  # not the capsule -- nothing to check

    path = Path(file_path)
    if not path.is_file():
        sys.exit(0)

    if tomllib is None:
        # Cannot validate without a parser; do not block the edit.
        sys.exit(0)

    try:
        parsed = tomllib.loads(path.read_bytes().decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        sys.stderr.write(
            "capsule.toml is not valid TOML after this edit: %s\n"
            "Fix the syntax so the SessionStart injector can read it.\n" % exc
        )
        sys.exit(2)

    errs = schema_errors(parsed)
    if errs:
        sys.stderr.write(
            "capsule.toml failed schema validation:\n"
            + "\n".join("  - " + e for e in errs)
            + "\nRequired non-empty string keys: %s.\n" % ", ".join(REQUIRED)
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
