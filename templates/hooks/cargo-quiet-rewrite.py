"""PreToolUse hook: auto-route verbose cargo commands through cargo-quiet.sh.

Deterministic output-filtering, NOT opt-in. The agent runs `cargo test` (or
build/clippy/check) and this hook transparently rewrites the `cargo <sub>` token
to `bash "$CLAUDE_PROJECT_DIR/scripts/cargo-quiet.sh" <sub>`, so the output is
born-filtered to warnings/errors/test-results + a verdict, with the full log one
Read away. Because the agent never sees a barrier (and full detail is always
reachable), there is nothing to work around -- unlike an opt-in wrapper it must
remember, or a filter that hides detail it then fights to recover.

Only test / build / clippy / check are rewritten (the verbose, high-token
subcommands). tree / metadata / fmt / doc / run are left alone. The `cargo`
token is rewritten in place, so it works inside `cd src && export ... && cargo
test ...` chains; the absolute "$CLAUDE_PROJECT_DIR" path survives the `cd`.

Bypass: put CARGO_QUIET=0 anywhere in the command to run raw cargo.
No-op if cargo-quiet is already in the command (no double-wrap).
"""
import json
import os
import re
import sys

# `cargo` as a command token (not xcargo, not a /path/cargo, not --cargo),
# immediately followed by one of the verbose subcommands.
CARGO = re.compile(r"(?<![\w./+-])cargo(\s+(?:test|build|clippy|check)\b)")

WRAPPER = 'bash "$CLAUDE_PROJECT_DIR/scripts/cargo-quiet.sh"'


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")
    if not command or "cargo-quiet" in command or "CARGO_QUIET=0" in command:
        sys.exit(0)

    # Only act when the wrapper is actually reachable for this session.
    proj = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not proj or not os.path.isfile(os.path.join(proj, "scripts", "cargo-quiet.sh")):
        sys.exit(0)

    fixed = CARGO.sub(WRAPPER + r"\1", command)
    if fixed == command:
        sys.exit(0)

    updated = dict(tool_input)
    updated["command"] = fixed
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "Routed cargo through cargo-quiet.sh (filtered output; full log path printed)",
            "updatedInput": updated,
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
