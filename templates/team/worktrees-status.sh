#!/usr/bin/env bash
# worktrees-status.sh -- git-truth bird's-eye of teammate worktrees.
#
# Per live worktree branch: the declared STATE (from .claude/team-digest/,
# written by the TeammateIdle digest hook), commits ahead/behind main, and
# merged? -- straight from ancestry, never from the lead's memory. Read this
# on demand; nothing here is cached in the lead's context.
#
# Usage: bash worktrees-status.sh [main-branch]   (default main)
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "not in a git repo"; exit 1; }
cd "$ROOT"
DIGEST_DIR=".claude/team-digest"
MAIN="${1:-main}"

# Latest declared state for a branch, scanned from the digest headers.
# Header line shape (from teammate-digest.py): "## <name> @ <ts> | branch=<br> | state=<S> | team=<t>"
state_for() {
  local br="$1" line
  [ -d "$DIGEST_DIR" ] || { echo "WORKING"; return; }
  line="$(grep -h "branch=$br " "$DIGEST_DIR"/*.md 2>/dev/null | tail -1)"
  if [ -n "$line" ]; then
    echo "$line" | sed -n 's/.*state=\([A-Z-]*\).*/\1/p'
  else
    echo "WORKING"
  fi
}

printf '%-30s %-16s %-12s %-7s %s\n' BRANCH STATE AHEAD/BEHIND MERGED WORKTREE
git worktree list --porcelain | awk '
  /^worktree /{wt=$2}
  /^branch /{print wt" "$2}
' | while read -r wt ref; do
  br="${ref#refs/heads/}"
  [ "$br" = "$MAIN" ] && continue
  ab="$(git rev-list --left-right --count "$MAIN...$br" 2>/dev/null | awk '{print $2"/"$1}')"
  if git merge-base --is-ancestor "$br" "$MAIN" 2>/dev/null; then merged=yes; else merged=no; fi
  printf '%-30s %-16s %-12s %-7s %s\n' "$br" "$(state_for "$br")" "${ab:-?/?}" "$merged" "$wt"
done

echo
echo "STATE: READY-FOR-MERGE -> safe-merge it at a seam | WAITING-FEEDBACK -> your call needed | BLOCKED -> stuck | WORKING -> not idle yet"
echo "MERGED=yes means the branch tip is already in $MAIN (git ancestry). Never merge or re-merge on memory."
