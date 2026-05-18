"""PreToolUse hook: rewrite Windows-hostile Bash constructs to safe equivalents.

Native Windows only (Git Bash). Before a Bash command runs, this hook rewrites:
  - redirect to `nul`  ->  redirect to `/dev/null`
        On Git Bash/MSYS2, `nul` is not a device -- redirecting to it creates a
        literal file named `nul` that cannot be deleted through normal means.
  - `python3`          ->  `python`
        Native Windows ships the launcher as `python` (or `py`), not `python3`.

It rewrites rather than blocks, so Claude never sees a failure and never burns a
turn retrying. No-op on WSL/Linux/macOS, where both forms are already correct.

The guardrail hook still runs in parallel; genuinely destructive commands are
denied regardless of what this hook returns (deny beats allow).
"""

import json
import re
import sys

# Redirect operators (>, >>, 1>, 2>, 2>>, &>, &>>) then `nul` as a whole word
# (not `nullable`, not a `nul.txt` filename).
NUL_REDIRECT = re.compile(r"((?:\d*|&)>>?)\s*nul(?![\w.])", re.IGNORECASE)

# `python3` as a standalone command token (not `python3.11`, not `python3-foo`).
PYTHON3 = re.compile(r"(?<![\w.-])python3(?![\w.-])")


def rewrite(command):
    out = NUL_REDIRECT.sub(r"\1 /dev/null", command)
    out = PYTHON3.sub("python", out)
    return out


def main():
    if sys.platform != "win32":
        sys.exit(0)  # `nul` and `python3` are correct on WSL/Linux/macOS

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")
    if not command:
        sys.exit(0)

    fixed = rewrite(command)
    if fixed == command:
        sys.exit(0)  # nothing Windows-hostile in this command

    updated = dict(tool_input)
    updated["command"] = fixed
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "Auto-corrected Windows-hostile shell syntax",
            "updatedInput": updated,
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
