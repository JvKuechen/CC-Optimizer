#!/usr/bin/env python3
"""PreToolUse(Bash) guard: a subagent must never `git commit` on the shared main checkout.

A subagent committing on the shared main tree bypasses the adversarial-review-before-merge
gate. This recurs whenever a worktree subagent's worktree is auto-cleaned after a no-op run
and a SendMessage-resume lands the subagent on main -- it then commits there directly. With
many worktree spawns in a parallel run, that needs a deterministic backstop, not vigilance.

Same fail-safe discriminator as the SessionStart role hook: agent_id is present ONLY inside
a subagent call. Blocks (exit 2) only when ALL hold:
  - the Bash command is a `git commit` (commit-producing form)
  - the call is inside a subagent (agent_id present)
  - the git toplevel is NOT under .claude/worktrees/ (i.e. the shared main checkout)
The lead (no agent_id) committing on main is allowed -- integration is its job. A subagent
committing inside its own worktree is allowed.

Wire as a PreToolUse hook with matcher "Bash":
  {"hooks": {"PreToolUse": [
    {"matcher": "Bash",
     "hooks": [{"type": "command",
                "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/subagent-commit-guard.py\""}]}
  ]}}
"""
import json
import re
import subprocess
import sys


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        sys.exit(0)

    cmd = data.get("tool_input", {}).get("command", "")
    # `git commit`, `git -C path commit`, `git commit -m ...`; not `git commit-graph`.
    if not re.search(r"\bgit\b.*\bcommit\b(?!-graph)", cmd):
        sys.exit(0)

    # Only subagents carry agent_id; the lead does not.
    if not data.get("agent_id"):
        sys.exit(0)

    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    ).stdout.strip().replace("\\", "/")
    if "/.claude/worktrees/" in top:
        sys.exit(0)  # inside its own worktree -- fine

    sys.stderr.write(
        "BLOCKED: a subagent must not `git commit` on the shared main checkout -- "
        "this bypasses the adversarial-review-before-merge gate. Call EnterWorktree first, "
        "or return your work to the lead (STATE: READY/BLOCKED) for integration. If your "
        "worktree was auto-cleaned after a no-op run, ask the lead to re-dispatch fresh "
        "rather than resuming onto main.\n"
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
