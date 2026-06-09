#!/usr/bin/env python3
"""SessionStart(compact) role-posture re-assertion -- fail-safe coordinator/executor.

Re-injects the correct role posture after a compaction so the coordinator-vs-executor
distinction survives the compaction that otherwise erases it. Wire it as a SessionStart
hook with matcher "compact":

  {"hooks": {"SessionStart": [
    {"matcher": "compact",
     "hooks": [{"type": "command",
                "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/sessionstart-coordinator.py\""}]}
  ]}}

FAIL-SAFE: only a positively-proven coordinator gets the coordinator posture. Every
ambiguous case gets executor (subthread) discipline, because a rogue coordinator that
merges neighbors is catastrophic while a scoped executor is harmless. Coordinator-hood
must be proven by ALL of:
  - no agent_id   (not an Agent-tool background subagent; agent_id is present only inside
                   a subagent call -- the documented way to tell subagent from main thread)
  - no agent_type (not a --agent / subagent session)
  - cwd is NOT under .claude/worktrees/  (not a worktree subthread)
  - a .claude/coordinator.marker file exists in cwd  (the lead created it at STEP 0;
    gitignore it and exclude it from .worktreeinclude so it never reaches a worktree)

Residual gap by design: a solo subthread sharing the MAIN checkout (no worktree) reads as
coordinator -- which is why worktree-isolated subthreads are the default model.
"""
import json
import os
import sys


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        sys.exit(0)

    # Only re-assert after a compaction. Other sources exit silently.
    if data.get("source") != "compact":
        sys.exit(0)

    cwd = data.get("cwd") or os.getcwd()
    in_worktree = ".claude/worktrees/" in cwd.replace("\\", "/")
    has_marker = os.path.isfile(os.path.join(cwd, ".claude", "coordinator.marker"))

    is_coordinator = (
        data.get("agent_id") is None
        and not data.get("agent_type")
        and not in_worktree
        and has_marker
    )

    if is_coordinator:
        ctx = (
            "POST-COMPACTION ROLE RE-ASSERTION -- YOU ARE THE COORDINATOR (MAIN THREAD).\n"
            "You delegate; you do not execute. Before anything else:\n"
            "1. Read handoff.md NOW -- the durable spine: role, settled decisions, in-flight delegations.\n"
            "2. Check worker readiness from git truth (team/worktrees-status.sh if present), not memory.\n"
            "3. Rebuild the in-chat bounty board from git log + handoff.md.\n"
            "TWO-STRIKES RULE: any edit that does not compile+test green on the FIRST try is no longer a\n"
            "quick fix -- stash it and delegate to a background worktree subagent. Lead-held work-in-progress\n"
            "dies at the next compaction; delegated worktree work survives and re-invokes you on completion.\n"
            "Bias hard toward delegation."
        )
    else:
        ctx = (
            "POST-COMPACTION ROLE RE-ASSERTION -- YOU ARE A SCOPE-DISCIPLINED EXECUTOR (SUBTHREAD).\n"
            "You are NOT the coordinator. Do not merge branches, do not spawn subthreads, do not touch\n"
            "neighboring units or other worktrees.\n"
            "1. Re-read your task brief (this session's opening prompt or your worktree brief file).\n"
            "2. Stay strictly in declared scope; surface other findings in the close-out, do not fix inline.\n"
            "3. Finish your one task, stage only your task's paths, return a structured close-out (STATE: line first)."
        )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": ctx,
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
