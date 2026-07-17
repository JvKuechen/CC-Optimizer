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
    MIN="${2:?test-oracle: --min needs a number}"
    shift 2
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

if [ "$total" -lt "$MIN" ]; then
    echo "test-oracle: vacuous run -- $total test(s) passed, $MIN required" >&2
    exit 1
fi
echo "test-oracle: $total test(s) passed (floor $MIN)"
