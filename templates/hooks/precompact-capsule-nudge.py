#!/usr/bin/env python3
"""PreCompact stale-capsule nudge -- the deterministic seam enforcer.

The context-handoff protocol's one fatal-if-forgotten seam is pre-compact:
compaction destroys the context the capsule edit would have distilled. This
hook makes forgetting impossible without ever writing the capsule itself --
the seam edit stays coordinator-authored; the hook only checks that it
happened.

Staleness test: capsule.toml's mtime predates this session's first
transcript event, i.e. no capsule edit has landed during this session.

Behavior by trigger (the manual/auto split is load-bearing):
  manual  stale -> exit 2. Compaction is refused and the stderr message is
          shown to the user: do the seam edit, then /compact again. This is
          exactly the protocol's ordering, enforced.
  auto    stale -> warn on stderr, allow. Blocking an auto-compact is only
          safe when it fired proactively; when it fires to recover from a
          context-limit error already returned by the API, a block fails
          the request outright -- and the hook input cannot distinguish the
          two cases. The SessionStart injection still carries the last
          capsule, so an auto-compact with a stale capsule degrades soft.

Overrides (never wedge):
  - /compact <anything containing "capsule-ok">  -- one-shot bypass
  - CAPSULE_NUDGE_DISABLE=1                      -- disable entirely
  - no capsule.toml in the project               -- silent no-op
  - unreadable transcript / no timestamp found   -- silent allow

Wire in .claude/settings.json (no matcher: fires for manual and auto, the
script branches on `trigger`):

  {"hooks": {"PreCompact": [
    {"hooks": [{"type": "command",
                "command": "python \"$CLAUDE_PROJECT_DIR/templates/hooks/precompact-capsule-nudge.py\""}]}
  ]}}

Capsule discovery mirrors handoff-capsule.py: CLAUDE_CAPSULE_FILE override,
else <project root>/capsule.toml.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCAN_LINES = 200  # transcript lines to scan for the first timestamped event


def first_event_epoch(transcript_path):
    """Epoch of the session's first timestamped transcript event, or the
    file's creation time as fallback, or None when nothing is readable."""
    path = Path(transcript_path)
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for _, line in zip(range(SCAN_LINES), fh):
                try:
                    stamp = json.loads(line).get("timestamp")
                except (json.JSONDecodeError, AttributeError):
                    continue
                if not isinstance(stamp, str):
                    continue
                try:
                    dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.timestamp()
    except OSError:
        return None
    try:
        return path.stat().st_ctime  # creation time on Windows
    except OSError:
        return None


def main():
    if os.environ.get("CAPSULE_NUDGE_DISABLE") == "1":
        sys.exit(0)

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        sys.exit(0)

    repo = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd())
    capsule = Path(os.environ.get("CLAUDE_CAPSULE_FILE") or (repo / "capsule.toml"))
    if not capsule.is_file():
        sys.exit(0)  # not a coordination workspace

    instructions = payload.get("custom_instructions") or ""
    if "capsule-ok" in instructions:
        sys.exit(0)

    transcript = payload.get("transcript_path")
    if not transcript:
        sys.exit(0)
    session_start = first_event_epoch(transcript)
    if session_start is None:
        sys.exit(0)  # cannot establish a baseline -- allow rather than wedge

    try:
        capsule_mtime = capsule.stat().st_mtime
    except OSError:
        sys.exit(0)

    if capsule_mtime >= session_start:
        sys.exit(0)  # seam edit landed this session

    age_h = (session_start - capsule_mtime) / 3600.0
    trigger = payload.get("trigger", "")
    if trigger == "manual":
        print(
            "capsule-nudge: capsule.toml has not been edited this session "
            "(last write %.1fh before the session's first event). Compaction "
            "would destroy the context the seam edit distills. Do the capsule "
            "seam edit, then /compact again -- or bypass once with "
            "/compact capsule-ok <instructions>." % age_h,
            file=sys.stderr,
        )
        sys.exit(2)

    # auto: proactive-vs-recovery is indistinguishable here; a blocked
    # recovery compact fails the in-flight request, so warn and allow.
    print(
        "capsule-nudge: auto-compact with a stale capsule.toml "
        "(last write %.1fh before session start) -- fold a seam edit in "
        "after compaction." % age_h,
        file=sys.stderr,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
