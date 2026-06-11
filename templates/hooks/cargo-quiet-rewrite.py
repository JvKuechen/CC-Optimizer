"""PreToolUse hook: auto-route verbose cargo commands through cargo-quiet.sh.

Deterministic output-filtering rather than opt-in. The agent runs `cargo test` (or
build/clippy/check) and this hook transparently rewrites the `cargo <sub>` token
to `bash "<abs path>/scripts/cargo-quiet.sh" <sub>`, so the output is
born-filtered to warnings/errors/test-results + a verdict, with the full log one
Read away. Because the agent never sees a barrier (and full detail is always
reachable), there is nothing to work around -- unlike an opt-in wrapper it must
remember, or a filter that hides detail it then fights to recover.

Only test / build / clippy / check are rewritten (the verbose, high-token
subcommands). tree / metadata / fmt / doc / run are left alone. The `cargo`
token is rewritten in place, so it works inside `cd src && export ... && cargo
test ...` chains. The wrapper path is embedded absolute (resolved from the
hook's own CLAUDE_PROJECT_DIR env): the executing Bash shell is not guaranteed
to carry that variable, so a literal "$CLAUDE_PROJECT_DIR" in the command can
expand empty and resolve to /scripts/cargo-quiet.sh (observed, exit 127).

CONSUMED-OUTPUT SKIP: when the command pipes, redirects, or captures output
(a non-`||` pipe, a `>` redirect, `$(...)` / backtick substitution), the
caller is parsing that output -- rewriting under it changes the shape being
parsed (observed: `cargo clippy 2>&1 | grep '^error'` matched nothing against
the filtered lines and shipped a false green). Those commands run raw cargo:
deliberately over-broad, because skipping only costs tokens while rewriting a
consumed stream costs correctness.

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

# Output is consumed downstream: a single pipe (`|` / `|&`, not `||`), any
# `>` redirect, or command substitution. Matching the whole command rather
# than just the cargo segment is the safe over-approximation.
CONSUMED = re.compile(r"(?<!\|)\|(?!\|)|>|\$\(|`")


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
    if CONSUMED.search(command):
        sys.exit(0)

    # Only act when the wrapper is actually reachable for this session.
    proj = os.environ.get("CLAUDE_PROJECT_DIR", "")
    wrapper_path = os.path.join(proj, "scripts", "cargo-quiet.sh")
    if not proj or not os.path.isfile(wrapper_path):
        sys.exit(0)

    wrapper = 'bash "{}"'.format(wrapper_path)
    fixed = CARGO.sub(lambda m: wrapper + m.group(1), command)
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
