#!/usr/bin/env python3
"""CI-status summary -- surface failing GitHub Actions runs at the right cadence.

A gate that sits red for several pushes unnoticed protects nothing. This hook checks the
default branch's recent workflow runs and surfaces any whose latest COMPLETED run failed
(which workflow, the consecutive-failure streak, the commit, when).

CADENCE -- wire it where breaks actually surface:
  * MERGE GATE (recommended for a long-running coordinator that delegates to subagents):
    PreToolUse(Bash); the hook fires only on `git merge`, so the coordinator sees "is the
    last-pushed baseline red?" right as it goes to integrate the next branch -- the moment
    to NOT stack on red and to put a fix on the board. Matches the push cadence.
      {"hooks": {"PreToolUse": [
        {"matcher": "Bash",
         "hooks": [{"type":"command","command":"python \"$CLAUDE_PROJECT_DIR/.claude/hooks/ci-status.py\""}]}
      ]}}
  * SESSION START (for restart-heavy layouts): SessionStart, no matcher.

Either way it reflects the last PUSHED state (CI hasn't run on local unpushed merges) -- which
is the correct semantic: "before I integrate/push more, is the baseline red?".

Graceful + quiet: no-ops silently if `gh` is absent/unauthed, there are no runs, the command
isn't a merge (in PreToolUse mode), or every workflow is green. Requires `gh` installed + authed.
"""
import json
import re
import subprocess
import sys

BAD = {"failure", "cancelled", "timed_out", "startup_failure", "action_required"}


def sh(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=20)
    except Exception:
        return None


def default_branch():
    r = sh(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
    if r and r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().split("/")[-1]
    return "main"


def failing_summary(branch):
    r = sh(["gh", "run", "list", "--branch", branch, "--limit", "40",
            "--json", "workflowName,conclusion,status,headSha,createdAt"])
    if not r or r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        runs = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    per_wf = {}
    for run in runs:
        per_wf.setdefault(run.get("workflowName", "?"), []).append(run)
    failing = []
    for wf, wf_runs in per_wf.items():
        completed = [x for x in wf_runs if x.get("status") == "completed"]
        if not completed or completed[0].get("conclusion") not in BAD:
            continue
        streak = 0
        for x in completed:
            if x.get("conclusion") in BAD:
                streak += 1
            else:
                break
        failing.append((wf, completed[0].get("conclusion"), streak,
                        (completed[0].get("headSha") or "")[:8],
                        (completed[0].get("createdAt") or "")[:16]))
    if not failing:
        return None
    lines = ["CI STATUS -- failing workflow(s) on `%s` (last pushed state):" % branch]
    for wf, concl, streak, sha, since in sorted(failing, key=lambda f: -f[2]):
        s = " (%d consecutive)" % streak if streak > 1 else ""
        lines.append("  - %s: %s%s, latest %s @ %s" % (wf, concl, s, sha, since))
    lines.append("A red gate protects nothing -- put a fix on the board before stacking/pushing "
                 "more. `gh run view --log-failed` for the error.")
    return "\n".join(lines)


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        sys.exit(0)

    # Event detection: PreToolUse(Bash) carries tool_input; gate it to `git merge` so it
    # fires at the integration cadence, not on every shell command.
    if "tool_input" in data:
        cmd = data.get("tool_input", {}).get("command", "")
        if not re.search(r"\bgit\b.*\bmerge\b", cmd):
            sys.exit(0)
        event = "PreToolUse"
    else:
        event = "SessionStart"

    summary = failing_summary(default_branch())
    if not summary:
        sys.exit(0)  # gh absent/unauthed, or all green -> silent

    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": summary}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
