#!/usr/bin/env python3
"""SessionStart handoff-capsule injector -- single-file state, zero re-mining.

Reads handoff.md from the project root and injects ONLY the marker-delimited
live-state capsule into context, so a fresh/resumed/post-compact session starts
oriented instead of re-reading (or re-deriving) the whole handoff narrative.

Wire it in the project's .claude/settings.json WITHOUT a matcher, so it fires
on every SessionStart source (startup, resume, compact, clear):

  {"hooks": {"SessionStart": [
    {"hooks": [{"type": "command",
                "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/handoff-capsule.py\""}]}
  ]}}

Capsule shape inside handoff.md (one block near the top; in-place edits for
current truth, append-only wave closeouts BELOW the block):

  <!-- CLAUDE_HANDOFF_CAPSULE_BEGIN -->
  ## ROLE
  ## CURRENT GOAL
  ## CURRENT STATE
  ## ACTIVE WAVE
  ## HOLDS AND GATES
  ## NEXT SAFE ACTION
  ## OPEN FOLLOW-ONS
  <!-- CLAUDE_HANDOFF_CAPSULE_END -->

Design verdicts (settled in the optimizer thread, 2026-06-10):
  - Inject on EVERY SessionStart source. The capsule costs ~1-2k tokens;
    one avoided state-rediscovery pass pays for weeks of injections.
  - COORDINATOR-ONLY: skip silently for subagents (agent_id / agent_type
    present) and worktree subthreads (cwd under .claude/worktrees/). A scoped
    executor must not inherit the coordinator's NEXT SAFE ACTION.
  - Degrade QUIETLY when markers are missing: fall back to a small
    top-of-handoff heuristic plus one self-heal line asking the session to add
    markers on its next handoff update. A loud failure would block sessions
    over a formatting issue.
  - The extractor is marker-based ONLY. The heading set above is convention;
    enforcing it is a (later, optional) validator's job, surfaced here as a
    prepended warning line -- never a commit gate, since handoff.md is
    gitignored and commit hooks cannot see it.
"""
import json
import os
import re
import sys
from pathlib import Path

CAPSULE_BEGIN = "<!-- CLAUDE_HANDOFF_CAPSULE_BEGIN -->"
CAPSULE_END = "<!-- CLAUDE_HANDOFF_CAPSULE_END -->"
MAX_CHARS = 8000

SELF_HEAL = (
    "NOTE: handoff.md has no capsule markers yet. On your next handoff update, "
    "wrap the live-state block (ROLE / CURRENT GOAL / CURRENT STATE / ACTIVE WAVE / "
    "HOLDS AND GATES / NEXT SAFE ACTION / OPEN FOLLOW-ONS) in "
    + CAPSULE_BEGIN + " ... " + CAPSULE_END + " so future sessions start oriented."
)


def is_executor(data):
    """Fail-safe: anything not positively the main thread gets no capsule."""
    if data.get("agent_id") is not None or data.get("agent_type"):
        return True
    cwd = data.get("cwd") or os.getcwd()
    return ".claude/worktrees/" in cwd.replace("\\", "/")


def extract_marked_capsule(text):
    start = text.find(CAPSULE_BEGIN)
    end = text.find(CAPSULE_END)
    if start == -1 or end == -1 or end <= start:
        return None
    body = text[start + len(CAPSULE_BEGIN):end].strip()
    return body or None


def extract_heading_block(text, heading_prefix):
    """First '## <heading_prefix>...' section, up to the next '## '."""
    pattern = re.compile(r"^##\s+" + re.escape(heading_prefix) + r".*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return None
    nxt = re.search(r"^##\s+", text[match.end():], re.MULTILINE)
    end = match.end() + nxt.start() if nxt else len(text)
    return text[match.start():end].strip()


def fallback_capsule(text):
    parts = []
    for heading in ("ROLE", "RESUME HERE", "RESUME", "CURRENT STATE", "Current State"):
        block = extract_heading_block(text, heading)
        if block and block not in parts:
            parts.append("\n".join(block.splitlines()[:80]).strip())
        if len(parts) == 2:
            break
    if not parts:
        return SELF_HEAL
    return "\n\n".join(parts) + "\n\n" + SELF_HEAL


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        data = {}

    if is_executor(data):
        sys.exit(0)

    repo = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())
    handoff = repo / "handoff.md"
    if not handoff.is_file():
        sys.exit(0)
    text = handoff.read_text(encoding="utf-8")

    capsule = extract_marked_capsule(text) or fallback_capsule(text)
    body = capsule[:MAX_CHARS].rstrip()

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                "HANDOFF CAPSULE (auto-injected from handoff.md) -- this IS the current "
                "state; trust it before searching for state elsewhere. Keep it true: "
                "update the capsule IN PLACE as truth changes, append wave closeouts "
                "below it in handoff.md.\n" + body
            ),
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
