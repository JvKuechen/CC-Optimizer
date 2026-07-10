#!/usr/bin/env python3
"""Stop-hook ticket gate -- "loop until a gate you control says done."

Fires when Claude tries to end its turn. If a ticket in tickets/ has
status = "in_progress", the session may only stop once the ticket's gate is
met; otherwise the stop is blocked and the failure detail is fed back as the
next turn's guidance. Sessions with no in_progress ticket stop normally, so
the gate costs nothing outside loop work.

The gate, in order (fail fast, cheap first):
  1. Every [[ac]] check command exits 0 (run from the repo root via bash).
  2. The working tree is clean (tracked files) -- gate what will merge,
     not a moving target.
  3. When gate.review = "codex": findings/codex-review-<ticket-id>.md exists,
     is newer than HEAD's commit time, and contains an Accept verdict with no
     Reject and no PROVISIONAL. A missing/stale report blocks with the exact
     codex-review.sh invocation to run.
On full pass the hook flips the ticket to status = "review" (ready for
merge; a human or the outer loop flips it to done) and allows the stop.

Circuit breakers, layered:
  - gate.max_gate_rounds (default 5): after that many blocked stops on one
    ticket, the hook flips the ticket to status = "blocked" with an
    auto-filled question and ALLOWS the stop -- the queue never spins on a
    ticket the gate keeps rejecting; a human decision is required to reopen.
  - Claude Code's own cap: 8 consecutive Stop-hook blocks, then the turn
    ends regardless.
  - Escalation is always available to the worker: set status = "blocked",
    fill [blocked].question, and the gate lets the session stop.

Escape hatch: LOOP_GATE_DISABLE=1 skips the gate entirely.
Rounds state lives at findings/loop-gate-state.json (gitignored).

Wire in .claude/settings.json (timeout must cover the AC checks; a test
suite that needs 10 minutes needs a timeout above 600):

  {"hooks": {"Stop": [
    {"hooks": [{"type": "command",
                "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/loop-gate.py\"",
                "timeout": 1800}]}
  ]}}
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    tomllib = None

TAIL_CHARS = 2000  # per failing check, kept small so the feedback stays readable


def block(reason):
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def repo_root(payload):
    for candidate in (os.environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd"), os.getcwd()):
        if candidate and Path(candidate).is_dir():
            return Path(candidate)
    return Path.cwd()


def load_tickets(tickets_dir):
    tickets = []
    for path in sorted(tickets_dir.glob("*.toml")):
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError):
            continue  # ticket-validate.py owns schema feedback at edit time
        tickets.append((path, data))
    return tickets


def run_check(cmd, cwd, timeout):
    try:
        proc = subprocess.run(
            ["bash", "-lc", cmd],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return 127, "bash not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, "timed out after %ss" % timeout
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output[-TAIL_CHARS:]


def git(root, *args):
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(root), capture_output=True, text=True, timeout=60
        )
        return proc.returncode, (proc.stdout or "").strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 1, ""


def set_ticket_status(path, new_status, blocked_question=None):
    """Targeted line rewrites keep the human-authored file layout intact
    (a TOML re-serialize would drop every comment, including the ACs')."""
    text = path.read_text(encoding="utf-8")
    text, n = re.subn(
        r'^(status\s*=\s*)"[a-z_]+"',
        r'\g<1>"%s"' % new_status,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if not n:
        return False
    if blocked_question:
        safe = blocked_question.replace("\\", "\\\\").replace('"', '\\"')
        text, n = re.subn(
            r'(\[blocked\][^\[]*?question\s*=\s*)""',
            r'\g<1>"%s"' % safe.replace("\\", "\\\\"),
            text,
            count=1,
            flags=re.DOTALL,
        )
        if not n and "[blocked]" not in text:
            text += '\n[blocked]\nquestion = "%s"\n' % safe
        # a [blocked] table with a question already filled is left as-is
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def load_rounds(state_file):
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_rounds(state_file, rounds):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(rounds, indent=2), encoding="utf-8", newline="\n")


def main():
    if os.environ.get("LOOP_GATE_DISABLE") == "1":
        sys.exit(0)
    if tomllib is None:
        sys.exit(0)  # no parser -- do not wedge sessions

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}

    root = repo_root(payload)
    tickets_dir = Path(os.environ.get("LOOP_TICKETS_DIR") or root / "tickets")
    if not tickets_dir.is_dir():
        sys.exit(0)

    tickets = load_tickets(tickets_dir)
    active = [(p, t) for p, t in tickets if t.get("status") == "in_progress"]
    if not active:
        sys.exit(0)
    if len(active) > 1:
        names = ", ".join(p.name for p, _ in active)
        block(
            "loop-gate: %d tickets are in_progress at once (%s). One ticket "
            "per session: set the others back to ready or blocked, then stop again."
            % (len(active), names)
        )

    path, ticket = active[0]
    ticket_id = ticket.get("id", path.stem)
    gate = ticket.get("gate") or {}
    max_rounds = gate.get("max_gate_rounds", 5)
    check_timeout = gate.get("check_timeout", 600)
    review_mode = gate.get("review", "codex")
    base = gate.get("base", "main")

    state_file = root / "findings" / "loop-gate-state.json"
    rounds = load_rounds(state_file)
    spent = rounds.get(ticket_id, 0)
    if spent >= max_rounds:
        question = (
            "loop-gate circuit breaker: gate rejected %d consecutive stops on %s. "
            "A human decision is required -- see the last gate feedback in the "
            "session transcript, then reset status to ready or in_progress to reopen."
            % (spent, ticket_id)
        )
        set_ticket_status(path, "blocked", blocked_question=question)
        rounds.pop(ticket_id, None)
        save_rounds(state_file, rounds)
        print("loop-gate: %s auto-blocked after %d rounds" % (ticket_id, spent), file=sys.stderr)
        sys.exit(0)

    def block_round(reason):
        rounds[ticket_id] = spent + 1
        save_rounds(state_file, rounds)
        block(
            "%s\n\n[loop-gate: round %d/%d on %s. If a decision only a human can "
            "make is what is stuck, set status = \"blocked\" and fill "
            "[blocked].question instead of retrying.]"
            % (reason, spent + 1, max_rounds, ticket_id)
        )

    # 1. AC checks -- the held-out mechanical oracle.
    failures = []
    for ac in ticket.get("ac") or []:
        code, tail = run_check(ac.get("check", "false"), root, check_timeout)
        if code != 0:
            failures.append(
                "%s FAILED (exit %d): %s\n%s" % (ac.get("id"), code, ac.get("check"), tail)
            )
    if failures:
        block_round(
            "loop-gate: %d of %d acceptance checks failing on %s:\n\n%s"
            % (len(failures), len(ticket.get("ac") or []), ticket_id, "\n\n".join(failures))
        )

    # 2. Clean tree -- the reviewed/gated state must be the committed state.
    # findings/ is excluded: the gate's own state file and the review report
    # live there and must not wedge the gate when findings/ isn't gitignored.
    code, dirty = git(
        root, "status", "--porcelain", "--untracked-files=no",
        "--", ".", ":(exclude)findings",
    )
    if code == 0 and dirty:
        block_round(
            "loop-gate: acceptance checks pass but the working tree has "
            "uncommitted tracked changes on %s:\n%s\nCommit the ticket's work, "
            "then stop again." % (ticket_id, dirty[:TAIL_CHARS])
        )

    # 3. Cross-vendor review verdict.
    if review_mode == "codex":
        report = root / "findings" / ("codex-review-%s.md" % ticket_id)
        invocation = (
            "bash scripts/codex-review.sh --base %s --tag %s "
            "--closeout-text \"<your close-out report>\"" % (base, ticket_id)
        )
        if not report.is_file():
            block_round(
                "loop-gate: %s acceptance checks pass; cross-vendor review still "
                "required. Run:\n  %s\nwait for it to complete, then stop again."
                % (ticket_id, invocation)
            )
        _, head_time = git(root, "log", "-1", "--format=%ct")
        if head_time and report.stat().st_mtime < int(head_time):
            block_round(
                "loop-gate: review report %s predates HEAD -- it reviewed an "
                "older state. Re-run:\n  %s" % (report.name, invocation)
            )
        text = report.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\bREJECT(?:ED)?\b", text, re.IGNORECASE):
            block_round(
                "loop-gate: Codex review verdict on %s is Reject. Address the "
                "findings in %s, commit, re-run the review, then stop again."
                % (ticket_id, report.as_posix())
            )
        if re.search(r"\bPROVISIONAL\b", text):
            block_round(
                "loop-gate: Codex review on %s carries PROVISIONAL findings "
                "(claims needing a toolchain run). Resolve them (run what the "
                "reviewer could not, or fix), re-run the review, then stop again."
                % ticket_id
            )
        if not re.search(r"\bACCEPT(?:ED)?\b", text, re.IGNORECASE):
            block_round(
                "loop-gate: no verdict found in %s. Re-run the review:\n  %s"
                % (report.name, invocation)
            )

    # Gate met: hand the ticket to the merge step and let the session end.
    set_ticket_status(path, "review")
    rounds.pop(ticket_id, None)
    save_rounds(state_file, rounds)
    print("loop-gate: %s gate met -> status review" % ticket_id, file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
