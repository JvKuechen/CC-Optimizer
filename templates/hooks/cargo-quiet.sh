#!/usr/bin/env bash
#
# cargo-quiet.sh -- run a cargo command but show the agent only the SIGNAL:
# warnings, errors, panics, and test-result lines, plus a one-line verdict.
# The full output is teed to a log whose path is printed, so "more detail" is
# one Read away -- never a re-run. This is "log levels for tool output": the
# default surfaces what needs action, the base output stays fully available.
#
# DEPLOY: copy to the workspace's scripts/ directory. The companion PreToolUse
# hook (templates/hooks/cargo-quiet-rewrite.py) routes verbose cargo commands
# through it automatically and expects it at scripts/cargo-quiet.sh.
#
# WHY: a green `cargo test`/`cargo build` emits hundreds of "Compiling ..."
# and "test ... ok" lines that cost tokens and carry no signal. An agent only
# needs "all green" when it is green, and the exact warning/error when it is
# not. Unlike an output filter that HIDES detail (which agents then fight to
# get around), this hides nothing -- the log path is right there -- so there is
# nothing to circumvent.
#
# USAGE (drop-in for cargo; pass the usual env + args):
#   bash scripts/cargo-quiet.sh test -p my-crate
#   CARGO_TARGET_DIR=~/build/target bash scripts/cargo-quiet.sh build -p my-crate
#   FULL=1 bash scripts/cargo-quiet.sh test ...     # also echo the full log
#   CARGO_QUIET_LOG=/path/run.log bash scripts/cargo-quiet.sh ...   # pin the log path
set -uo pipefail

LOG="${CARGO_QUIET_LOG:-$(mktemp /tmp/cargo-quiet-XXXX.log)}"

cargo "$@" >"$LOG" 2>&1
status=$?

# Signal lines: compiler diagnostics + their location/expectation context, test
# results, failure blocks, panics. Capped so a flood of errors stays readable.
SIGNAL="$(grep -nE '^(warning|error)(\[|:)|^\s*-->|expected .* found|^test result:|^failures:|panicked|cannot find|unresolved import|error: could not compile' "$LOG" | head -250)"
[ -n "$SIGNAL" ] && printf '%s\n' "$SIGNAL"

# Verdict line. grep -c prints the count and exits 1 on no match -- capture it,
# then blank a zero so the suffix only shows when there is something to show.
warns=$(grep -cE '^warning(\[|:)' "$LOG" 2>/dev/null) || true
[ "$warns" = "0" ] && warns=""
oktests=$(grep -E '^test result: ok' "$LOG" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' | paste -sd+ - 2>/dev/null | bc 2>/dev/null) || true
if [ "$status" -eq 0 ]; then
  echo "cargo-quiet: OK (cargo $* exit 0)${oktests:+ -- ${oktests} tests passed}${warns:+, ${warns} warning(s) above}"
else
  echo "cargo-quiet: FAILED (cargo $* exit $status) -- signal above"
fi
# Self-documenting drill-down: signal lines are 'N:...' where N is the log line.
echo "  full log: $LOG  |  context around a line: sed -n 'N-3,N+3p' $LOG  |  search: grep -nC3 '<pat>' $LOG  |  everything: read the file"

[ "${FULL:-}" = "1" ] && { echo "----- FULL LOG -----"; cat "$LOG"; }
exit $status
