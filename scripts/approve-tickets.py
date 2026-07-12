#!/usr/bin/env python3
"""Cross-vendor plan gate -- flip approved ticket drafts to ready.

The plan gate decides which tickets become dispatchable. The human form is
reading and approving each draft by hand; this script is the automated form:
for every tickets/*.toml with status = "draft", run the cross-vendor design
review (codex-review.sh --design) over the ticket file itself, parse the
report's terminal VERDICT line, and flip draft -> ready on ACCEPT. Anything
else stays draft, with the report path printed for the planner (or the
human) to address. Deterministic brick; the only LLM judgment is inside the
review itself.

What the reviewer gates on a ticket draft (the --design adapter in
codex-review.sh): premises verified against the repo, doctrine drift,
overcomplexity -- and the quality of the AC oracle itself: exact,
non-saturable checks two agents could not disagree about. That last one is
load-bearing: with the human out of the per-ticket loop, cross-vendor
scrutiny of the checks is what keeps a worker from being graded by a
rubber-stamp oracle. The merge step's habit stays regardless:
`git diff main...<branch> -- tickets/` must be empty.

Two deterministic guards ride on top of the verdict (bricks, not mortar):
  - An AC-less draft never flips, even on ACCEPT -- no oracle, no dispatch.
  - Falsification: on ACCEPT, every AC check is run against the
    pre-implementation tree. An oracle must be able to fail; a check that
    exits 0 before any work is a vacuous filter (cargo exits 0 on a
    zero-match test name -- the field-caught trap) or an already-satisfied
    state. Lone passes are surfaced as invariant-guard notes; an oracle
    where every check already passes gates nothing, so the draft holds.
    --skip-falsify opts out (e.g. checks too heavy for plan-gate time).

Usage (from the repo root):
    python scripts/approve-tickets.py                 # gate every draft
    python scripts/approve-tickets.py --ticket T-058  # gate one
    python scripts/approve-tickets.py --dry-run       # list drafts only
    python scripts/approve-tickets.py --effort high --model gpt-5.6
Env overrides: LOOP_TICKETS_DIR, CODEX_REVIEW_SCRIPT.
Exit: 0 when every gated draft flipped to ready; 1 otherwise.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    sys.exit("approve-tickets: needs Python 3.11+ (tomllib)")

# Same terminal-line parse as loop-gate.py: last match wins, template menu
# placeholders ('<ACCEPT | ...>') do not match.
VERDICT_RE = re.compile(
    r"^[\s#*>_-]*VERDICT\b[\s:*-]*(ACCEPT|CONDITIONAL|REJECT)\b",
    re.IGNORECASE | re.MULTILINE,
)


def parse_verdict(text):
    verdict = None
    for m in VERDICT_RE.finditer(text):
        verdict = m.group(1).upper()
    return verdict


def check_passes(bash, cmd, cwd, timeout):
    """True when the check exits 0. Unrunnable/timed-out counts as failing
    (non-vacuous): the falsification pass only flags checks that PASS."""
    try:
        proc = subprocess.run(
            [bash, "-lc", cmd], cwd=str(cwd),
            capture_output=True, text=True, timeout=timeout,
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def flip_to_ready(path):
    """Targeted line rewrite (a TOML re-serialize would drop the comments)."""
    text = path.read_text(encoding="utf-8")
    text, n = re.subn(
        r'^(status\s*=\s*)"draft"', r'\g<1>"ready"', text, count=1, flags=re.MULTILINE
    )
    if not n:
        return False
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def main():
    ap = argparse.ArgumentParser(description="cross-vendor plan gate over draft tickets")
    ap.add_argument("--ticket", help="gate only this ticket id")
    ap.add_argument("--dry-run", action="store_true", help="list drafts, run nothing")
    ap.add_argument("--effort", help="pass through to codex-review.sh")
    ap.add_argument("--model", help="pass through to codex-review.sh")
    ap.add_argument("--timeout", type=int, default=1800, help="seconds per review (default 1800)")
    ap.add_argument("--skip-falsify", action="store_true",
                    help="skip the pre-implementation falsification run of AC checks")
    args = ap.parse_args()

    root = Path.cwd()
    tickets_dir = Path(os.environ.get("LOOP_TICKETS_DIR") or root / "tickets")
    review_script = Path(
        os.environ.get("CODEX_REVIEW_SCRIPT") or root / "scripts" / "codex-review.sh"
    )
    if not tickets_dir.is_dir():
        sys.exit("approve-tickets: no tickets dir at %s" % tickets_dir)

    drafts = []
    for path in sorted(tickets_dir.glob("*.toml")):
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError) as exc:
            print("approve-tickets: skipping unparseable %s: %s" % (path.name, exc), file=sys.stderr)
            continue
        tid = data.get("id", path.stem)
        if data.get("status") == "draft" and (not args.ticket or args.ticket == tid):
            drafts.append((path, tid, data))

    if not drafts:
        print("approve-tickets: no draft tickets%s" % (" matching %s" % args.ticket if args.ticket else ""))
        return 0
    if args.dry_run:
        for path, tid, data in drafts:
            has_acs = bool(data.get("ac"))
            print("draft: %s (%s)%s" % (tid, path.as_posix(), "" if has_acs else "  [no ACs -- reviewable, not flippable]"))
        return 0
    if not review_script.is_file():
        sys.exit("approve-tickets: review script not found: %s" % review_script)

    # which("bash"): a bare "bash" on Windows resolves System32 (WSL) before
    # PATH; forward slashes: bash swallows backslashed paths.
    bash = os.environ.get("LOOP_GATE_BASH") or shutil.which("bash") or "bash"

    results = []
    for path, tid, data in drafts:
        acs = data.get("ac") or []
        tag = "%s-plan" % tid
        cmd = [bash, review_script.as_posix(), "--design", path.as_posix(), "--tag", tag]
        if args.effort:
            cmd += ["--effort", args.effort]
        if args.model:
            cmd += ["--model", args.model]
        print("approve-tickets: reviewing %s (foreground, tag=%s)..." % (tid, tag))
        try:
            proc = subprocess.run(cmd, cwd=str(root), timeout=args.timeout)
        except subprocess.TimeoutExpired:
            results.append((tid, "TIMEOUT", None))
            continue
        report = root / "findings" / ("codex-review-%s.md" % tag)
        if proc.returncode != 0 or not report.is_file():
            results.append((tid, "REVIEW-FAILED (exit %d)" % proc.returncode, None))
            continue
        text = report.read_text(encoding="utf-8", errors="replace")
        verdict = parse_verdict(text) or "NO-VERDICT"
        provisional = len(re.findall(r"\bPROVISIONAL\b", text))
        if verdict == "ACCEPT" and not acs:
            # No [[ac]] blocks = no oracle. A reviewer can ACCEPT the design
            # thinking; only a ticket that carries its checks may go ready.
            results.append((tid, "ACCEPT but no [[ac]] -- stays draft (author the AC oracle first)", report))
        elif verdict == "ACCEPT":
            # Falsification pass: an oracle must be able to fail. Run each
            # check against the pre-implementation tree; exit 0 there means a
            # vacuous filter (cargo exits 0 on a zero-match test name) or an
            # already-satisfied state. An invariant guard ("clippy stays
            # clean") legitimately passes, so lone passes are surfaced as
            # notes -- but an oracle where EVERY check already passes gates
            # nothing and the draft holds.
            pre_pass = []
            if not args.skip_falsify:
                ct = (data.get("gate") or {}).get("check_timeout", 600)
                for ac in acs:
                    if check_passes(bash, ac.get("check", "false"), root, ct):
                        pre_pass.append(ac.get("id") or "?")
            if pre_pass and len(pre_pass) == len(acs):
                results.append((tid, "ACCEPT but every AC check already passes pre-implementation -- oracle gates nothing, stays draft", report))
            else:
                for ac_id in pre_pass:
                    print("approve-tickets: note -- %s %s already passes pre-implementation (invariant guard or vacuous filter -- confirm which)" % (tid, ac_id))
                flipped = flip_to_ready(path)
                results.append((tid, "ACCEPT -> ready" if flipped else "ACCEPT (flip failed!)", report))
        else:
            results.append((tid, "%s -- stays draft" % verdict, report))
        if provisional:
            print("approve-tickets: note -- %d PROVISIONAL finding(s) in %s (implementation leg runs the toolchain)" % (provisional, report.name))

    print("\n=== plan gate results ===")
    ok = True
    for tid, outcome, report in results:
        print("%-8s %s%s" % (tid, outcome, ("  [%s]" % report.as_posix()) if report else ""))
        if not outcome.startswith("ACCEPT -> ready"):
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
