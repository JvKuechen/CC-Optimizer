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
# Platform note: the brokers are native processes. On native Windows,
# Git Bash's `ps` lists only MSYS processes and would silently report zero
# brokers, so enumeration and kill go through PowerShell CIM + taskkill
# there; Linux/WSL/macOS use ps/pkill.
#
# USAGE
#   bash scripts/sweep-stale-brokers.sh --dry-run   # list only
#   bash scripts/sweep-stale-brokers.sh             # kill stale brokers
set -euo pipefail

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) WIN=1 ;;
  *) WIN=0 ;;
esac

# Emit "pid<TAB>command line" per broker process. The broker is a node
# daemon, so only node processes qualify -- without that constraint, any
# shell whose own command line quotes the marker string (an invoking
# wrapper, a grep, this script's ancestry) would match and its whole tree
# would be killed.
list_brokers() {
  if [ "$WIN" = 1 ]; then
    powershell.exe -NoProfile -Command \
      "Get-CimInstance Win32_Process -Filter \"Name='node.exe' AND CommandLine LIKE '%app-server-broker.mjs%'\" | ForEach-Object { \"\$(\$_.ProcessId)\`t\$(\$_.CommandLine)\" }" \
      2>/dev/null | tr -d '\r'
  else
    ps -eo pid=,args= | grep "app-server-broker.mjs" | grep -v grep \
      | awk '{pid=$1; sub(/^[ ]*[0-9]+[ ]+/, ""); print pid "\t" $0}' \
      | grep -E $'\t[^ ]*node( |$)'
  fi
}

kill_broker_tree() {
  pid=$1
  if [ "$WIN" = 1 ]; then
    # /T kills the whole tree (codex app-server child included); run inside
    # PowerShell so MSYS cannot path-mangle /PID.
    powershell.exe -NoProfile -Command "taskkill /PID $pid /T /F" >/dev/null 2>&1 || true
  else
    # children first (codex app-server), then the broker itself
    pkill -P "$pid" 2>/dev/null || true
    kill "$pid" 2>/dev/null || true
  fi
}

swept=0
while IFS=$'\t' read -r pid args; do
  [ -n "${pid:-}" ] || continue
  # --cwd value: quoted (may contain spaces) or bare token
  cwd=$(printf '%s\n' "$args" | grep -oE '\--cwd ("[^"]+"|[^ ]+)' | head -1 | sed 's/^--cwd //; s/^"//; s/"$//' || true)
  [ -n "$cwd" ] || continue
  if [ ! -d "$cwd" ]; then
    if [ "$DRY" = 1 ]; then
      echo "would sweep broker $pid (cwd gone: $cwd)"
    else
      kill_broker_tree "$pid"
      echo "swept broker $pid (cwd gone: $cwd)"
    fi
    swept=$((swept + 1))
  fi
done < <(list_brokers)

echo "sweep: $swept stale broker(s)$([ "$DRY" = 1 ] && echo ' (dry run)')"
