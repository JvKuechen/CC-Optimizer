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
            drafts.append((path, tid))

    if not drafts:
        print("approve-tickets: no draft tickets%s" % (" matching %s" % args.ticket if args.ticket else ""))
        return 0
    if args.dry_run:
        for path, tid in drafts:
            print("draft: %s (%s)" % (tid, path.as_posix()))
        return 0
    if not review_script.is_file():
        sys.exit("approve-tickets: review script not found: %s" % review_script)

    results = []
    for path, tid in drafts:
        tag = "%s-plan" % tid
        # which("bash"): a bare "bash" on Windows resolves System32 (WSL)
        # before PATH; forward slashes: bash swallows backslashed paths.
        bash = os.environ.get("LOOP_GATE_BASH") or shutil.which("bash") or "bash"
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
        if verdict == "ACCEPT":
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
