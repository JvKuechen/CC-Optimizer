#!/usr/bin/env bash
# safe-merge.sh <branch> [--keep] -- lead-timed, lock-gated, HEAD-verified
# merge of a teammate worktree branch into main.
#
# Refuses while a build/E2E lock is held (worktrees hold, never land mid-build),
# fast-forward merges, then CONFIRMS the commit is in HEAD before returning
# success -- so "tested main without the fix" is impossible. By default it tears
# the merged worktree+branch down (the train is complete); pass --keep to skip
# teardown when the teammate process is still live in that worktree.
#
# Build/E2E lock convention: the lead writes .claude/integration.lock at the
# start of a provision/build/E2E run and removes it when done. While present,
# this script holds.
set -uo pipefail

BR="${1:-}"
[ -n "$BR" ] || { echo "usage: safe-merge.sh <branch> [--keep]"; exit 2; }
KEEP=0; [ "${2:-}" = "--keep" ] && KEEP=1

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "not in a git repo"; exit 1; }
cd "$ROOT"
MAIN=main
LOCK=".claude/integration.lock"

[ -f "$LOCK" ] && { echo "BLOCKED: $LOCK present (build/E2E in progress). Worktree holds -- retry at a seam."; exit 3; }
git rev-parse --verify "$BR" >/dev/null 2>&1 || { echo "no such branch: $BR"; exit 1; }

cur="$(git rev-parse --abbrev-ref HEAD)"
[ "$cur" = "$MAIN" ] || { echo "checkout $MAIN first (currently on '$cur')"; exit 1; }
# -uno: ignore untracked files (the board/digest/lock dirs). A ff merge only
# touches tracked content, so untracked files never make it unsafe.
[ -z "$(git status --porcelain -uno)" ] || { echo "$MAIN has tracked changes -- commit or stash first"; exit 1; }

tip="$(git rev-parse "$BR")"
if ! git merge --ff-only "$BR"; then
  echo "NOT FAST-FORWARD: $BR has diverged from $MAIN. Rebase the worktree on $MAIN, then retry (keeps the train linear)."
  exit 1
fi
if git merge-base --is-ancestor "$tip" HEAD; then
  echo "MERGED: $tip ($BR) is now in $MAIN HEAD -- safe to build/test."
else
  echo "MERGE VERIFY FAILED: $tip not in HEAD"; exit 1
fi

if [ "$KEEP" = "1" ]; then
  echo "kept worktree+branch (--keep). Remove once the teammate is shut down:"
  echo "  git worktree remove --force <path> ; git branch -d $BR"
else
  wt="$(git worktree list --porcelain | awk -v b="refs/heads/$BR" '/^worktree /{w=$2} /^branch /&&$2==b{print w}')"
  [ -n "$wt" ] && git worktree remove --force "$wt" 2>/dev/null && echo "removed worktree $wt"
  git branch -d "$BR" 2>/dev/null && echo "removed branch $BR"
fi
