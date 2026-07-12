#!/usr/bin/env python3
"""Stop-hook ticket gate -- "loop until a gate you control says done."

Fires when Claude tries to end its turn. If a ticket in tickets/ has
status = "in_progress", the session may only stop once the ticket's gate is
met; otherwise the stop is blocked and the failure detail is fed back as the
next turn's guidance. Sessions with no in_progress ticket stop normally, so
the gate costs nothing outside loop work.

The gate, in order (fail fast, cheap first):
  1. The working tree is clean, untracked files included -- gate what will
     merge, not a moving target. A new source file that was never `git add`ed
     is the classic works-locally-broken-on-merge, so untracked blocks too
     (scratch belongs in .gitignore; findings/ is excluded either way).
  2. Every [[ac]] check command exits 0 (run from the repo root via bash).
  3. When gate.review = "codex": findings/codex-review-<ticket-id>.md exists,
     is newer than HEAD's commit time, and its terminal "VERDICT:" line reads
     ACCEPT or CONDITIONAL (the rubric's machine-parseable last line; parsing
     that line alone keeps `Rejected:`-style labels inside findings from
     reading as the verdict). PROVISIONAL findings block regardless. A report
     without a VERDICT line falls back to the legacy whole-text scan. A
     missing/stale report blocks with the exact codex-review.sh invocation
     to run.
On full pass the hook flips the ticket to status = "review" (ready for
merge; a human or the outer loop flips it to done) and allows the stop.

Review-status re-engagement (the T-007 wrinkle): a ticket whose status is
already "review" re-gates when the session keeps working past the flip --
detected as a dirty tracked tree, commits newer than the recorded
gated_head, or no recorded gated_head at all (a self-flip that never
passed the gate). This applies ONLY off the primary branch (default
main/master, override LOOP_GATE_PRIMARY_BRANCH): on the lead's checkout
HEAD moves whenever any other ticket merges, so review tickets there are
the merge queue, not live work, and gating them would false-block the
lead. On the primary branch the merge-time verdict read stays the net.

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


def load_state(state_file):
    """State schema: {"rounds": {id: int}, "gated_head": {id: sha}}.
    A legacy file holding a flat {id: int} map is read as rounds."""
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"rounds": {}, "gated_head": {}}
    if data and all(isinstance(v, int) for v in data.values()):
        return {"rounds": data, "gated_head": {}}
    return {
        "rounds": data.get("rounds") or {},
        "gated_head": data.get("gated_head") or {},
    }


def save_state(state_file, state):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8", newline="\n")


def last_code_commit(root):
    """Hash + committer time of the newest commit touching non-bookkeeping
    paths. Ticket-status flips and findings churn are bookkeeping -- they
    must not stale a verdict or re-engage the gate."""
    code, out = git(
        root, "log", "-1", "--format=%H %ct",
        "--", ".", ":(exclude)tickets", ":(exclude)findings",
    )
    if code != 0 or not out:
        return "", 0
    parts = out.split()
    try:
        return parts[0], int(parts[1])
    except (IndexError, ValueError):
        return "", 0


def on_primary_branch(root):
    primary = os.environ.get("LOOP_GATE_PRIMARY_BRANCH")
    code, branch = git(root, "branch", "--show-current")
    if code != 0 or not branch:
        return True  # detached/unknown: err toward not re-gating
    if primary:
        return branch == primary
    return branch in ("main", "master")


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

    state_file = root / "findings" / "loop-gate-state.json"
    state = load_state(state_file)

    tickets = load_tickets(tickets_dir)
    active = [(p, t) for p, t in tickets if t.get("status") == "in_progress"]
    if not active:
        # Review-status re-engagement: off the primary branch, a "review"
        # ticket whose gated_head no longer matches HEAD (or was never
        # recorded -- a self-flip) re-enters the gate.
        if on_primary_branch(root):
            sys.exit(0)
        code_head, _ = last_code_commit(root)
        _, dirty_now = git(
            root, "status", "--porcelain", "--untracked-files=normal",
            "--", ".", ":(exclude)findings",
        )
        stale = [
            (p, t) for p, t in tickets
            if t.get("status") == "review"
            and (dirty_now or state["gated_head"].get(t.get("id", p.stem)) != code_head)
        ]
        if not stale:
            sys.exit(0)
        active = stale[:1]
    elif len(active) > 1:
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

    rounds = state["rounds"]
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
        save_state(state_file, state)
        print("loop-gate: %s auto-blocked after %d rounds" % (ticket_id, spent), file=sys.stderr)
        sys.exit(0)

    def block_round(reason):
        rounds[ticket_id] = spent + 1
        save_state(state_file, state)
        block(
            "%s\n\n[loop-gate: round %d/%d on %s. If a decision only a human can "
            "make is what is stuck, set status = \"blocked\" and fill "
            "[blocked].question instead of retrying.]"
            % (reason, spent + 1, max_rounds, ticket_id)
        )

    # 1. Clean tree first (cheap): the gated state must be the committed
    # state, and the expensive AC runs then exercise exactly what merges.
    # Untracked files count -- a new source file that was never `git add`ed
    # passes local AC runs but is absent from the reviewed diff and the
    # merge (scratch belongs in .gitignore). findings/ is excluded: the
    # gate's own state file and the review report live there and must not
    # wedge the gate when findings/ isn't gitignored.
    code, dirty = git(
        root, "status", "--porcelain", "--untracked-files=normal",
        "--", ".", ":(exclude)findings",
    )
    if code == 0 and dirty:
        block_round(
            "loop-gate: the working tree has uncommitted or untracked "
            "changes on %s:\n%s\nCommit the ticket's work (git add new "
            "source files; gitignore scratch), then stop again."
            % (ticket_id, dirty[:TAIL_CHARS])
        )

    # 2. AC checks -- the held-out mechanical oracle.
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
        _, code_time = last_code_commit(root)
        if code_time and report.stat().st_mtime < code_time:
            block_round(
                "loop-gate: review report %s predates the last code commit -- "
                "it reviewed an older state. Re-run:\n  %s"
                % (report.name, invocation)
            )
        text = report.read_text(encoding="utf-8", errors="replace")
        # Authoritative verdict: the rubric's terminal "VERDICT: <token>"
        # line. Parsing this line alone keeps `Rejected:`-style labels inside
        # findings (the reviewer's licensed house style) from reading as the
        # verdict. Last matching line wins; a report without one (written
        # against the pre-VERDICT rubric) falls back to the whole-text scan.
        verdict = None
        for m in re.finditer(
            r"^[\s#*>_-]*VERDICT\b[\s:*-]*(ACCEPT|CONDITIONAL|REJECT)\b",
            text, re.IGNORECASE | re.MULTILINE,
        ):
            verdict = m.group(1).upper()
        legacy_reject = verdict is None and re.search(
            r"\bREJECT(?:ED)?\b", text, re.IGNORECASE
        )
        if verdict == "REJECT" or legacy_reject:
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
        if verdict is None and not re.search(r"\bACCEPT(?:ED)?\b", text, re.IGNORECASE):
            block_round(
                "loop-gate: no verdict found in %s. Re-run the review (the "
                "current rubric emits a terminal VERDICT: line):\n  %s"
                % (report.name, invocation)
            )
        if verdict == "CONDITIONAL":
            print(
                "loop-gate: %s verdict is CONDITIONAL -- follow-ups ride in "
                "%s for the merge step" % (ticket_id, report.as_posix()),
                file=sys.stderr,
            )

    # Gate met: hand the ticket to the merge step and let the session end.
    # gated_head pins the exact commit this pass covered, so a later commit
    # in the same session re-engages the gate instead of riding the flip.
    set_ticket_status(path, "review")
    rounds.pop(ticket_id, None)
    code_head, _ = last_code_commit(root)
    if code_head:
        state["gated_head"][ticket_id] = code_head
    save_state(state_file, state)
    print("loop-gate: %s gate met -> status review" % ticket_id, file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
