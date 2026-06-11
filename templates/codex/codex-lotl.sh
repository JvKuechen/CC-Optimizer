#!/usr/bin/env bash
#
# codex-lotl.sh -- run Codex (`codex exec`, read-only sandbox) as a
# lay-of-the-land surveyor over a crate or subsystem, using the workspace's
# own lay-of-the-land rubric as the survey criteria.
#
# DEPLOY: copy to the workspace's scripts/ directory. Requires the
# lay-of-the-land agent at .claude/agents/lay-of-the-land.md (banked
# alongside this script at templates/agents/) and the Codex CLI on PATH,
# logged in.
#
# WHY THIS EXISTS
# ---------------
# The lead dispatches the `lay-of-the-land` subagent at session start to get
# an independent read on the area it is about to touch, in parallel with its
# own orientation. This script lets Codex carry that survey instead -- same
# five-lens criteria, same return format. Pairs with codex-review.sh: both
# are second-opinion engines driven by `codex exec`.
#
# Unlike the reviewer rubric, the lay-of-the-land rubric has no
# Claude-team-only machinery (no transcript jumps), so it is fed nearly
# verbatim -- only the survey scope is appended. `codex exec -s read-only`
# keeps the tree untouched, matching the "identify, never edit" contract;
# no worktree needed.
#
# Backgrounded by the lead (Bash `run_in_background: true`); completion
# notification on shell exit. Verbose run -> log; the survey -> report via
# -o; full session persists under ~/.codex/sessions/.
#
# CONTRACT
# --------
#   Positional (required): <scope>  -- the crate or subsystem to survey,
#                                       e.g. "src/maintainer" or "the auth path"
#   Optional:
#     --tag <name>     label for output files (default: derived from scope)
#     --repo <dir>     repo/worktree to survey in (default: this repo root)
#     --rubric <file>  survey-criteria source (default: lay-of-the-land.md)
#     --model <model>  override Codex model (default: Codex default)
#     --effort <level> reasoning effort: minimal|low|medium|high (default: Codex default)
#
#   Writes (under the MAIN repo's findings/, gitignored):
#     findings/codex-lotl-<tag>.md     the survey (lead reads this)
#     findings/codex-lotl-<tag>.log    full Codex run (available if needed)
#
# USAGE
#   bash scripts/codex-lotl.sh src/maintainer --tag maintainer
#   bash scripts/codex-lotl.sh "the conn_auth challenge path" --tag connauth
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUBRIC="$REPO_ROOT/.claude/agents/lay-of-the-land.md"
OUTDIR="$REPO_ROOT/findings"

TARGET_REPO="$REPO_ROOT"
TAG=""
MODEL=""
EFFORT=""
SCOPE=""

die() { echo "codex-lotl: $*" >&2; exit 1; }

# Rebuild an absolute path with each component's TRUE on-disk casing (drvfs
# resolves WS/ws case-insensitively; casing is load-bearing on WSL).
canon() {
  python3 - "$1" 2>/dev/null <<'PY' || printf '%s' "$1"
import os, sys
real = os.sep
for part in os.path.abspath(sys.argv[1]).split(os.sep):
    if not part:
        continue
    try:
        entries = os.listdir(real)
    except OSError:
        real = os.path.join(real, part); continue
    real = os.path.join(real, next((e for e in entries if e.lower() == part.lower()), part))
print(real)
PY
}

while [ $# -gt 0 ]; do
  case "$1" in
    --tag)    TAG="$2"; shift 2 ;;
    --repo)   TARGET_REPO="$2"; shift 2 ;;
    --rubric) RUBRIC="$2"; shift 2 ;;
    --model)  MODEL="$2"; shift 2 ;;
    --effort) EFFORT="$2"; shift 2 ;;
    -h|--help) sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//; $d'; exit 0 ;;
    -*)       die "unknown flag: $1 (see --help)" ;;
    *)        [ -z "$SCOPE" ] && SCOPE="$1" || SCOPE="$SCOPE $1"; shift ;;
  esac
done

command -v codex >/dev/null 2>&1 || die "codex not on PATH. Install the CLI binary and run 'codex login'."
[ -n "$SCOPE" ] || die "no scope. Pass the crate/subsystem to survey (see --help)."
[ -f "$RUBRIC" ] || die "rubric not found: $RUBRIC"
[ -d "$TARGET_REPO" ] || die "repo dir not found: $TARGET_REPO"
case "$EFFORT" in ""|minimal|low|medium|high) ;; *) die "invalid --effort '$EFFORT' (minimal|low|medium|high)" ;; esac
# Canonicalize the repo path to its true on-disk casing (matters on WSL).
TARGET_REPO="$(canon "$TARGET_REPO")"
# Derive a filesystem-safe tag from the scope if none given.
[ -n "$TAG" ] || TAG="$(echo "$SCOPE" | tr -cs 'A-Za-z0-9' '-' | sed 's/^-//; s/-$//' | cut -c1-40)"

mkdir -p "$OUTDIR"
REPORT="$OUTDIR/codex-lotl-$TAG.md"
LOG="$OUTDIR/codex-lotl-$TAG.log"

# Strip only the leading YAML frontmatter block; preserve any body '---'.
RUBRIC_BODY="$(awk 'NR==1 && /^---$/{infm=1; next} infm && /^---$/{infm=0; next} !infm{print}' "$RUBRIC")"

PROMPT="$RUBRIC_BODY

----- THIS SURVEY -----
Survey scope: $SCOPE
You have read-only access to the repository. Read files, grep, and run
read-only commands (dependency-graph queries, reading docs and config) as
the criteria direct. Identify only; the read-only sandbox keeps the tree
untouched."

declare -a EXTRA_FLAGS=()
[ -n "$MODEL" ] && EXTRA_FLAGS+=(--model "$MODEL")
[ -n "$EFFORT" ] && EXTRA_FLAGS+=(-c "model_reasoning_effort=$EFFORT")

echo "codex-lotl: surveying '$SCOPE' in $TARGET_REPO (tag=$TAG${EFFORT:+, effort=$EFFORT})" >&2

# Prompt via stdin ('-') for parity with codex-review.sh and ARG_MAX safety.
printf '%s' "$PROMPT" | codex exec \
    -s read-only \
    -C "$TARGET_REPO" \
    "${EXTRA_FLAGS[@]}" \
    -o "$REPORT" \
    - >"$LOG" 2>&1 || {
  status=$?
  echo "codex-lotl: FAILED (exit $status). See $LOG" >&2
  exit $status
}

echo "codex-lotl: complete -> $REPORT  (full run: $LOG)"
