#!/usr/bin/env python3
"""PostToolUse ticket schema validator -- the deterministic guard.

Fires after Write/Edit. If the edited file is a ticket (a .toml file inside
a directory named tickets/), it parses the result and checks the schema; on
any failure it exits 2 with a message, which Claude Code feeds back to the
model so the bad edit is corrected immediately. Same doctrine as
capsule-validate.py: schema enforced for real, not advisory.

Wire it in .claude/settings.json as a PostToolUse hook matching Write|Edit:

  {"hooks": {"PostToolUse": [
    {"matcher": "Write|Edit",
     "hooks": [{"type": "command",
                "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/ticket-validate.py\""}]}
  ]}}

Schema (kept in lockstep with loop-gate.py and ticket-template.toml):
  required non-empty strings: id, title, status, context
  status enum:                draft | ready | in_progress | blocked | review | done
                              (draft = authored, awaiting plan-gate approval;
                              only ready is dispatchable)
  ac:                         non-empty list of tables, each with non-empty
                              string id, criterion, check; ids unique.
                              OPTIONAL while status is draft or blocked -- the
                              AC oracle is authored at the plan gate, so a
                              backlog stub may not carry it yet; every other
                              status requires it (and approve-tickets.py
                              refuses to flip an AC-less draft to ready)
  optional strings:           source, size, non_goals
  optional list of strings:   depends_on
  optional [gate] table:      review in {codex, none}; base string;
                              max_gate_rounds / check_timeout positive ints
  optional [blocked] table:   question/options/recommendation strings;
                              question REQUIRED non-empty when status=blocked
"""
import json
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    tomllib = None

STATUSES = ("draft", "ready", "in_progress", "blocked", "review", "done")
REQUIRED = ("id", "title", "status", "context")


def is_ticket(path):
    if path is None:
        return False
    p = Path(path)
    return p.suffix == ".toml" and "tickets" in [part.lower() for part in p.parts[:-1]]


def schema_errors(data):
    errs = []
    for key in REQUIRED:
        val = data.get(key)
        if not isinstance(val, str) or not val.strip():
            errs.append("key '%s' must be a non-empty string" % key)
    status = data.get("status")
    if isinstance(status, str) and status not in STATUSES:
        errs.append("status '%s' not one of %s" % (status, "|".join(STATUSES)))

    acs = data.get("ac")
    if not isinstance(acs, list) or not acs:
        # Pre-plan-gate stubs (draft, or blocked at planning time) may not
        # carry the AC oracle yet; every dispatchable-or-beyond status must.
        if status not in ("draft", "blocked"):
            errs.append(
                "at least one [[ac]] table is required once status leaves "
                "draft/blocked (the AC oracle is what the gate runs)"
            )
    else:
        seen = set()
        for i, ac in enumerate(acs):
            if not isinstance(ac, dict):
                errs.append("[[ac]] entry %d is not a table" % (i + 1))
                continue
            for key in ("id", "criterion", "check"):
                val = ac.get(key)
                if not isinstance(val, str) or not val.strip():
                    errs.append("[[ac]] entry %d: '%s' must be a non-empty string" % (i + 1, key))
            ac_id = ac.get("id")
            if ac_id in seen:
                errs.append("duplicate ac id '%s'" % ac_id)
            seen.add(ac_id)

    deps = data.get("depends_on")
    if deps is not None and not (
        isinstance(deps, list) and all(isinstance(x, str) for x in deps)
    ):
        errs.append("depends_on must be a list of strings")

    gate = data.get("gate")
    if gate is not None:
        if not isinstance(gate, dict):
            errs.append("[gate] must be a table")
        else:
            review = gate.get("review")
            if review is not None and review not in ("codex", "none"):
                errs.append("gate.review must be 'codex' or 'none'")
            base = gate.get("base")
            if base is not None and not (isinstance(base, str) and base.strip()):
                errs.append("gate.base must be a non-empty string")
            for key in ("max_gate_rounds", "check_timeout"):
                val = gate.get(key)
                if val is not None and not (isinstance(val, int) and val > 0):
                    errs.append("gate.%s must be a positive integer" % key)

    blocked = data.get("blocked")
    if blocked is not None and not isinstance(blocked, dict):
        errs.append("[blocked] must be a table")
    if status == "blocked":
        question = (blocked or {}).get("question")
        if not isinstance(question, str) or not question.strip():
            errs.append(
                "status is 'blocked' but blocked.question is empty -- "
                "state the open decision, options, and a recommendation"
            )
    return errs


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not is_ticket(file_path):
        sys.exit(0)

    path = Path(file_path)
    if not path.is_file():
        sys.exit(0)

    if tomllib is None:
        sys.exit(0)  # no parser available -- do not false-block

    try:
        ticket = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        print("ticket-validate: %s is not valid TOML: %s" % (path.name, exc), file=sys.stderr)
        sys.exit(2)

    errs = schema_errors(ticket)
    if errs:
        print(
            "ticket-validate: %s failed schema check:\n  - %s"
            % (path.name, "\n  - ".join(errs)),
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
