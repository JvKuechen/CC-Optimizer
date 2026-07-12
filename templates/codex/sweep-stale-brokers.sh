#!/usr/bin/env bash
#
# sweep-stale-brokers.sh -- kill codex app-server broker trees whose --cwd
# worktree no longer exists.
#
# Each Codex review leg run through the codex plugin leaves an
# app-server-broker.mjs daemon (plus its codex app-server child) bound to
# the worktree it served. They idle harmlessly, but accumulate across a
# wave and outlive worktree removal. Run this at wave teardown, AFTER
# removing merged worktrees -- a broker whose worktree directory is gone
# has nothing left to serve.
#
# USAGE
#   bash scripts/sweep-stale-brokers.sh --dry-run   # list only
#   bash scripts/sweep-stale-brokers.sh             # kill stale brokers
set -euo pipefail

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

swept=0
while read -r pid rest; do
  cwd=$(printf '%s\n' "$rest" | grep -oE '\--cwd [^ ]+' | head -1 | cut -d' ' -f2 || true)
  [ -n "$cwd" ] || continue
  if [ ! -d "$cwd" ]; then
    if [ "$DRY" = 1 ]; then
      echo "would sweep broker $pid (cwd gone: $cwd)"
    else
      # children first (codex app-server), then the broker itself
      pkill -P "$pid" 2>/dev/null || true
      kill "$pid" 2>/dev/null || true
      echo "swept broker $pid (cwd gone: $cwd)"
    fi
    swept=$((swept + 1))
  fi
done < <(ps -eo pid=,args= | grep "app-server-broker.mjs" | grep -v grep | awk '{pid=$1; $1=""; print pid $0}')

echo "sweep: $swept stale broker(s)$([ "$DRY" = 1 ] && echo ' (dry run)')"
