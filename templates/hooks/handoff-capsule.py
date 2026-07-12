#!/usr/bin/env python3
"""SessionStart capsule injector -- structured, schema-validated, queryable.

Reads capsule.toml from the project root and injects the live coordination
state into context, so a fresh/resumed/post-compact session starts oriented
instead of re-reading (or re-deriving) state from scattered prose.

The capsule is TOML, not markdown, on purpose: the state has known fields
(role / current_goal / current_state / ...), so a structured file gives back
schema enforcement (a PostToolUse validator, capsule-validate.py, rejects a
malformed edit) and queryability (tomllib / a one-line read) that hand-rolled
marker extraction over markdown only approximated. Wave HISTORY is not stored
here -- git log is the durable record; the capsule holds only live state.

Wire it in the project's .claude/settings.json WITHOUT a matcher so it fires
on every SessionStart source (startup, resume, compact, clear):

  {"hooks": {"SessionStart": [
    {"hooks": [{"type": "command",
                "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/handoff-capsule.py\""}]}
  ]}}

capsule.toml shape (flat keys for sed-survivability; one block, edited in
place as truth changes):

  schema_version = 1
  updated = "2026-06-10"
  thread = "cc-optimizer-main"
  role = \"\"\"...\"\"\"
  current_goal = \"\"\"...\"\"\"
  current_state = \"\"\"...\"\"\"
  active_wave = \"\"\"...\"\"\"           # optional ("none" is fine)
  holds_and_gates = ["...", "..."]      # optional list
  next_safe_action = \"\"\"...\"\"\"
  open_followons = ["...", "..."]       # optional list

Design verdicts (settled in the optimizer thread, 2026-06-10):
  - Inject on EVERY SessionStart source. The capsule costs ~1-2k tokens;
    one avoided state-rediscovery pass pays for weeks of injections.
  - COORDINATOR-ONLY: skip silently for subagents (agent_id / agent_type
    present) and worktree subthreads (cwd under .claude/worktrees/). A scoped
    executor must not inherit the coordinator's NEXT SAFE ACTION.
  - Structured + validated, not markdown + graceful-degradation. A malformed
    capsule fails LOUD: the validator blocks a bad write, and this injector
    surfaces a parse/schema error as a visible nudge rather than silently
    degrading (which hid drift). It still never BLOCKS a session over a
    formatting issue -- it injects what it can plus the error.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - older interpreters
    tomllib = None

MAX_CHARS = 8000

# (toml key, display heading). Order is the injection order.
SECTIONS = [
    ("role", "ROLE"),
    ("current_goal", "CURRENT GOAL"),
    ("current_state", "CURRENT STATE"),
    ("active_wave", "ACTIVE WAVE"),
    ("holds_and_gates", "HOLDS AND GATES"),
    ("next_safe_action", "NEXT SAFE ACTION"),
    ("open_followons", "OPEN FOLLOW-ONS"),
]
REQUIRED = ("role", "current_goal", "current_state", "next_safe_action")

PREAMBLE = (
    "HANDOFF CAPSULE (auto-injected from capsule.toml) -- this is the current "
    "state; trust it before searching for state elsewhere. It is the queryable "
    "source of truth, and the main thread is its only writer: update its fields "
    "in place at wave seams (wave close, direction change, pre-compact), folding "
    "worker close-outs into one edit (a PostToolUse validator rejects a "
    "malformed edit). Workers read it and report back through close-outs. Wave "
    "history lives in git log, not here.\n"
)


def is_executor(data):
    """Fail-safe: anything not positively the main thread gets no capsule."""
    if data.get("agent_id") is not None or data.get("agent_type"):
        return True
    cwd = data.get("cwd") or os.getcwd()
    return ".claude/worktrees/" in cwd.replace("\\", "/")


def schema_errors(data):
    """Return a list of human-readable schema problems (empty = valid)."""
    errs = []
    for key in REQUIRED:
        val = data.get(key)
        if val is None:
            errs.append("missing required key '%s'" % key)
        elif not isinstance(val, str) or not val.strip():
            errs.append("key '%s' must be a non-empty string" % key)
    for key in ("holds_and_gates", "open_followons"):
        if key in data and not (
            isinstance(data[key], list)
            and all(isinstance(x, str) for x in data[key])
        ):
            errs.append("key '%s' must be a list of strings" % key)
    return errs


def render(data):
    out = []
    for key, heading in SECTIONS:
        val = data.get(key)
        if val is None:
            continue
        if isinstance(val, list):
            if not val:
                continue
            body = "\n".join("- " + str(x) for x in val)
        else:
            body = str(val).strip()
            if not body:
                continue
        out.append("## %s\n%s" % (heading, body))
    return "\n\n".join(out)


MAX_LOG_LINES = 15
MAX_DIRTY_LINES = 10


def staleness_delta(repo, capsule_path):
    """Git-truth delta since the capsule's last write, or "" when current.

    This is what makes a stale capsule safe to inject: the post-compact (or
    next-morning) context receives the capsule PLUS exactly what it does not
    cover, so the pending seam edit can be folded from git truth instead of
    rediscovery. Auto-compact cannot be blocked on staleness (a blocked
    recovery compact fails the in-flight request), so the heal happens here,
    on the injection side.
    """
    try:
        mtime = capsule_path.stat().st_mtime
    except OSError:
        return ""
    since = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

    def run(*args):
        try:
            proc = subprocess.run(
                ["git", *args], cwd=str(repo),
                capture_output=True, text=True, timeout=10,
            )
            return proc.stdout.strip() if proc.returncode == 0 else ""
        except (OSError, subprocess.TimeoutExpired):
            return ""

    def capped(text, cap):
        lines = text.splitlines()
        body = "\n".join("- " + ln for ln in lines[:cap])
        if len(lines) > cap:
            body += "\n- ...and %d more" % (len(lines) - cap)
        return body

    log = run("log", "--oneline", "--no-decorate", "--since", since)
    dirty = run("status", "--porcelain", "--untracked-files=no")
    if not log and not dirty:
        return ""

    age_h = (time.time() - mtime) / 3600.0
    parts = [
        "## SINCE CAPSULE EDIT",
        "The capsule was last written %s (%.1fh ago). Git state has moved "
        "since then; a seam edit folding the items below into the capsule "
        "has not yet landed." % (since, age_h),
    ]
    if log:
        parts.append("Commits newer than the capsule:\n" + capped(log, MAX_LOG_LINES))
    if dirty:
        parts.append("Uncommitted tracked changes:\n" + capped(dirty, MAX_DIRTY_LINES))
    return "\n\n".join(parts)


def emit(context):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }))


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        data = {}

    if is_executor(data):
        sys.exit(0)

    repo = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())
    capsule_path = Path(os.environ.get("CLAUDE_CAPSULE_FILE") or (repo / "capsule.toml"))
    if not capsule_path.is_file():
        sys.exit(0)  # no capsule yet -- nothing to inject

    if tomllib is None:
        emit("CAPSULE: capsule.toml present but this Python lacks tomllib "
             "(need 3.11+). State not injected; upgrade the interpreter.")
        sys.exit(0)

    raw = capsule_path.read_bytes()
    try:
        parsed = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        emit(PREAMBLE + "## CAPSULE PARSE ERROR\ncapsule.toml is not valid TOML: "
             "%s\nFix it before relying on injected state." % exc)
        sys.exit(0)

    errs = schema_errors(parsed)
    body = render(parsed)[:MAX_CHARS].rstrip()

    context = PREAMBLE + body
    delta = staleness_delta(repo, capsule_path)
    if delta:
        context += "\n\n" + delta
    if errs:
        context += ("\n\n## CAPSULE SCHEMA WARNING\n"
                    + "\n".join("- " + e for e in errs)
                    + "\nThe capsule is incomplete; fix capsule.toml.")
    emit(context)
    sys.exit(0)


if __name__ == "__main__":
    main()
