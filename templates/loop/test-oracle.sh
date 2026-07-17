#!/usr/bin/env bash
#
# test-oracle.sh -- non-vacuous cargo-test runner for AC check commands.
#
# DEPLOY: copy to the workspace's scripts/ directory alongside
# approve-tickets.py. Cargo-flavored; port the passed-count parse when
# deploying to a non-Rust stack (the floor idea is stack-agnostic).
#
# Usage: bash scripts/test-oracle.sh [--min N] <cargo test args...>
#
# Runs `cargo test <args>` and succeeds only when the run PASSED at least
# N tests (default 1). This closes the whole zero-test-vacuous family the
# review gate exists to catch:
#   - absent integration target      -> cargo itself exits non-zero
#   - empty / misnamed target        -> 0 tests pass, floor fails the check
#   - filter matching nothing        -> 0 tests pass, floor fails the check
#   - real failure                   -> cargo exits non-zero
# Ticket AC checks that run tests go through this wrapper; hand-rolled
# `cargo test` pipelines in ACs are rejected at the plan gate.
set -euo pipefail

MIN=1
if [ "${1:-}" = "--min" ]; then
    MIN="${2:-}"
    shift 2 2>/dev/null || { echo "test-oracle: --min needs a value" >&2; exit 2; }
fi
# The floor IS the invariant: a zero, negative, garbage, or overflow floor
# would reopen the vacuous-run hole this script exists to close. Positive
# integers only, capped at 9 digits so the later arithmetic can never
# overflow bash's integer comparison (which error-OPENS inside an if).
if ! [[ "$MIN" =~ ^[1-9][0-9]{0,8}$ ]]; then
    echo "test-oracle: --min must be a positive integer (max 9 digits), got '${MIN}'" >&2
    exit 2
fi

out="$(cargo test "$@" 2>&1)" || {
    printf '%s\n' "$out"
    echo "test-oracle: cargo test exited non-zero" >&2
    exit 1
}
printf '%s\n' "$out"

# Sum "N passed" across every test binary in the run (unit, integration,
# doc). `test result: ok. 3 passed; ...`
total=0
while read -r n; do
    total=$((total + n))
done < <(printf '%s\n' "$out" | sed -n 's/^test result: ok\. \([0-9][0-9]*\) passed.*/\1/p')

# Inverted comparison so a comparison ERROR fails closed: if `[` cannot
# prove total >= MIN (including by erroring), the check fails.
if ! [ "$total" -ge "$MIN" ]; then
    echo "test-oracle: vacuous run -- $total test(s) passed, $MIN required" >&2
    exit 1
fi
echo "test-oracle: $total test(s) passed (floor $MIN)"
