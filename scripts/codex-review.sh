#!/usr/bin/env bash
#
# codex-review.sh -- run Codex (`codex exec`) as an adversarial reviewer over
# a diff, using the workspace's own adversarial-reviewer rubric as the single
# source of review criteria.
#
# DEPLOY: copy to the workspace's scripts/ directory. Requires the
# adversarial-reviewer agent at .claude/agents/adversarial-reviewer.md
# (banked alongside this script at templates/agents/) and the Codex CLI on
# PATH, logged in. Toolchain examples in the adapter prompt are Rust-flavored
# (cargo); adjust per stack when deploying to a non-Rust workspace.
#
# WHY THIS EXISTS
# ---------------
# The lead runs the `adversarial-reviewer` subagent (a Claude subagent) on a
# worker's diff before marking work complete. This script lets a second,
# independent engine (Codex) run the SAME review criteria, so the two can be
# A/B'd as reviewers and -- once trusted -- Codex can carry the review leg
# while Claude implements + folds.
#
# NOTE ON ENGINE: it deliberately does NOT use `codex exec review`. That
# subcommand refuses a custom [PROMPT] alongside any target selector
# (--commit / --base / --uncommitted all error "cannot be used with
# [PROMPT]"), so it can only run Codex's BUILT-IN reviewer -- which would
# defeat an A/B on identical criteria. Instead we compute the diff
# deterministically with git and feed it plus our rubric to `codex exec`.
#
# SANDBOX: for --commit / --base the review runs in a DISPOSABLE git
# worktree checked out at the reviewed ref, with `-s workspace-write`, so
# Codex can run the toolchain (clippy/tests) to verify lint-reachability and
# regression claims instead of REJECTing from inference. The worktree is
# removed after the run when it holds no tracked changes; CARGO_TARGET_DIR
# (if set) is granted as an extra writable root so builds hit the warm
# shared cache. --uncommitted reviews in place read-only (the changes exist
# only in the working tree), as does --read-only on any selector.
#
# The rubric is NOT duplicated -- we feed the agent file verbatim
# (frontmatter stripped) behind a short adapter preamble that redirects its
# Claude-team-only steps (teammate transcript jumps) to diff-based
# reasoning. One source of truth.
#
# The lead invokes this BACKGROUNDED via the Bash tool
# (`run_in_background: true`); the completion notification fires on shell
# exit. Codex's verbose run is redirected to a per-run log; the clean review
# report is captured by `-o` to a file the lead reads on the ping. The full
# session also persists under ~/.codex/sessions/.
#
# CONTRACT
# --------
#   Exactly one target selector is required:
#     --commit <sha>     review the change a single commit introduced
#     --base <branch>    review HEAD's delta vs a base branch (BASE...HEAD)
#     --uncommitted      review staged + unstaged changes
#   Optional:
#     --tag <name>       label for output files (default: derived from target)
#     --repo <dir>       repo/worktree to review in (default: this repo root)
#     --rubric <file>    review-criteria source (default: adversarial-reviewer.md)
#     --model <model>    override Codex model (default: Codex default)
#     --effort <level>   reasoning effort: minimal|low|medium|high (default:
#                        Codex's built-in default). Spend high on security/wire
#                        legs, low on mechanical renames.
#     --closeout-text <string>  the worker's close-out report, passed inline
#                        (the coordinator already holds it -- a worker's final
#                        message returns verbatim as the tool result). Injected
#                        into the prompt so the rubric's CLAIMS CROSS-CHECK step
#                        runs against the actual claims, and persisted to
#                        findings/<tag>-closeout.md as the durable copy.
#     --closeout <file>  the same report, read from a file instead. A missing
#                        file warns and the review proceeds without the
#                        cross-check. --closeout-text wins when both are given.
#     --read-only        review in place with the read-only sandbox (skip the
#                        disposable worktree + toolchain access).
#
#   Writes (under the MAIN repo's findings/, gitignored):
#     findings/codex-review-<tag>.md    clean review report (lead reads this)
#     findings/codex-review-<tag>.log   full Codex run (available if needed)
#
#   The --repo path is canonicalized to its TRUE on-disk casing (each
#   component matched against the real directory entry) so Codex cites it
#   right regardless of how the caller cased it -- casing is load-bearing on
#   WSL even though /mnt/c resolves case-insensitively, so readlink can't fix it.
#
# USAGE
#   bash scripts/codex-review.sh --commit a1b2c3d --tag legF
#   bash scripts/codex-review.sh --base main --repo .claude/worktrees/legG \
#        --tag legG --effort high --closeout findings/legG-closeout.md
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
RUBRIC="$REPO_ROOT/.claude/agents/adversarial-reviewer.md"
OUTDIR="$REPO_ROOT/findings"

TARGET_REPO="$REPO_ROOT"
TAG=""
MODEL=""
EFFORT=""
CLOSEOUT_IN=""
CLOSEOUT_TEXT=""
SELECTOR=""   # commit | base | uncommitted
SELVAL=""     # sha or branch
TARGET_DESC=""
READ_ONLY=0
WT=""         # disposable review worktree (set when toolchain mode is active)

die() { echo "codex-review: $*" >&2; exit 1; }

# Rebuild an absolute path with each component's TRUE on-disk casing. drvfs
# resolves WS/ws case-insensitively so readlink does NOT correct casing, but
# casing is load-bearing on WSL and in Codex's path citations.
canon() {
  # WSL-only rebuild: drvfs resolves /mnt/c case-insensitively so readlink does
  # not correct casing there. On native Windows Git Bash (MSYS) and plain Linux,
  # `pwd -P` paths already work with `git -C`, and forcing them through Windows
  # Python mangles the MSYS drive prefix (/c/... -> C:Users\...). Pass through.
  grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null || { printf '%s' "$1"; return; }
  python - "$1" 2>/dev/null <<'PY' || printf '%s' "$1"
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
    --commit)      SELECTOR="commit"; SELVAL="$2"; TARGET_DESC="commit $2"; [ -z "$TAG" ] && TAG="${2:0:7}"; shift 2 ;;
    --base)        SELECTOR="base";   SELVAL="$2"; TARGET_DESC="base $2";   shift 2 ;;
    --uncommitted) SELECTOR="uncommitted"; TARGET_DESC="uncommitted"; [ -z "$TAG" ] && TAG="uncommitted"; shift ;;
    --tag)         TAG="$2"; shift 2 ;;
    --repo)        TARGET_REPO="$2"; shift 2 ;;
    --rubric)      RUBRIC="$2"; shift 2 ;;
    --model)       MODEL="$2"; shift 2 ;;
    --effort)      EFFORT="$2"; shift 2 ;;
    --closeout)    CLOSEOUT_IN="$2"; shift 2 ;;
    --closeout-text) CLOSEOUT_TEXT="$2"; shift 2 ;;
    --read-only)   READ_ONLY=1; shift ;;
    -h|--help)     sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//; $d'; exit 0 ;;
    *)             die "unknown argument: $1 (see --help)" ;;
  esac
done

# Resolve the Codex CLI. A fresh shell inherits it from the system PATH, but a
# shell started BEFORE the CLI was installed (codex installed mid-session) keeps
# the old PATH until Claude Code restarts -- the exact stale-window that reads as
# "codex not found" right after a successful install. Fall back to the known
# install dirs so the review leg survives that window without a restart.
if ! command -v codex >/dev/null 2>&1; then
  for d in \
    "$HOME/AppData/Local/Programs/OpenAI/Codex/bin" \
    "$HOME/.cargo/bin" \
    "$HOME/.local/bin"; do
    if [ -x "$d/codex" ] || [ -x "$d/codex.exe" ]; then PATH="$d:$PATH"; export PATH; break; fi
  done
fi
command -v codex >/dev/null 2>&1 || die "codex not found on PATH or in known install dirs. Install the CLI and run 'codex login'. If you just installed it, restart Claude Code so new shells inherit the updated PATH."
[ -n "$SELECTOR" ] || die "no target selector. Pass one of --commit / --base / --uncommitted (see --help)."
[ -f "$RUBRIC" ] || die "rubric not found: $RUBRIC"
[ -d "$TARGET_REPO" ] || die "repo dir not found: $TARGET_REPO"
case "$EFFORT" in ""|minimal|low|medium|high) ;; *) die "invalid --effort '$EFFORT' (minimal|low|medium|high)" ;; esac
if [ -z "$CLOSEOUT_TEXT" ] && [ -n "$CLOSEOUT_IN" ] && [ ! -f "$CLOSEOUT_IN" ]; then
  echo "codex-review: WARNING closeout file not found ($CLOSEOUT_IN); proceeding without the claims cross-check" >&2
  CLOSEOUT_IN=""
fi
[ -n "$TAG" ] || TAG="review"

# Canonicalize the repo path to its true on-disk casing so Codex cites it right.
TARGET_REPO="$(canon "$TARGET_REPO")"

mkdir -p "$OUTDIR"
CLOSEOUT="$OUTDIR/codex-review-$TAG.md"
LOG="$OUTDIR/codex-review-$TAG.log"

# Inline close-out: persist the durable copy, then treat it like the file form.
if [ -n "$CLOSEOUT_TEXT" ]; then
  CLOSEOUT_IN="$OUTDIR/$TAG-closeout.md"
  printf '%s\n' "$CLOSEOUT_TEXT" > "$CLOSEOUT_IN"
fi

# Compute the diff under review deterministically (script = brick).
case "$SELECTOR" in
  commit)      DIFF="$(git -C "$TARGET_REPO" show --no-color "$SELVAL" 2>&1)" || die "git show $SELVAL failed: $DIFF" ;;
  base)        DIFF="$(git -C "$TARGET_REPO" diff --no-color "$SELVAL"...HEAD 2>&1)" || die "git diff $SELVAL...HEAD failed: $DIFF" ;;
  uncommitted) DIFF="$(git -C "$TARGET_REPO" diff --no-color HEAD 2>&1)" || die "git diff HEAD failed: $DIFF" ;;
esac
[ -n "$DIFF" ] || die "empty diff for $TARGET_DESC -- nothing to review."

# Toolchain mode (default for --commit / --base): a disposable worktree at the
# reviewed ref + workspace-write, so Codex can run the stack's lint/test
# commands to corroborate. Discarded after the run unless it holds tracked
# changes.
REVIEW_DIR="$TARGET_REPO"
SANDBOX="read-only"
cleanup_wt() {
  [ -n "$WT" ] || return 0
  if git -C "$WT" diff --quiet && git -C "$WT" diff --cached --quiet; then
    git -C "$TARGET_REPO" worktree remove --force "$WT" >/dev/null 2>&1 || true
  else
    echo "codex-review: review worktree kept (tracked changes present): $WT" >&2
  fi
  WT=""
}
if [ "$READ_ONLY" -eq 0 ] && [ "$SELECTOR" != "uncommitted" ]; then
  case "$SELECTOR" in
    commit) REF="$SELVAL" ;;
    base)   REF="HEAD" ;;
  esac
  REF="$(git -C "$TARGET_REPO" rev-parse --verify "$REF^{commit}")" || die "cannot resolve review ref '$REF'"
  WT="$REPO_ROOT/.claude/worktrees/codex-review-$TAG-$$"
  git -C "$TARGET_REPO" worktree add --detach "$WT" "$REF" >/dev/null 2>&1 || die "worktree add failed at $REF"
  trap cleanup_wt EXIT
  REVIEW_DIR="$WT"
  SANDBOX="workspace-write"
fi

# Rubric body = the agent file with its LEADING YAML frontmatter block
# stripped. Strips only the first ---...--- (when line 1 is a fence); any
# '---' horizontal rule inside the body is preserved.
RUBRIC_BODY="$(awk 'NR==1 && /^---$/{infm=1; next} infm && /^---$/{infm=0; next} !infm{print}' "$RUBRIC")"

# Adapter: bridge the rubric's Claude-team-only mechanics (teammate
# transcript jumps) to a transcript-less external reviewer working from the
# diff. Everything substantive -- the seven signs, staging/doctrine/
# test-quality checks, the return format -- carries over unchanged. Two
# variants: toolchain mode (disposable worktree, may run the toolchain) and
# read-only mode (in-place, non-building corroboration only).
if [ "$SANDBOX" = "workspace-write" ]; then
read -r -d '' ADAPTER <<'EOF' || true
You are an external adversarial reviewer working inside a disposable git
worktree checked out at the exact code under review (your cwd). The diff under
review is included verbatim at the end of this message. You have write access
to this worktree and may run the project's toolchain (for a Rust workspace:
cargo clippy, cargo test, cargo tree, cargo metadata) to corroborate findings;
the worktree is discarded after the review, so nothing you write or build
ships. Use the repo to grep for prior art, read the CLAUDE.md settled
decisions, and inspect seam tests -- exactly the corroboration the criteria
call for. Claude teammate transcripts are outside your reach here; wherever
the criteria say to confirm a finding via a teammate's transcript, reason
instead from the diff plus what you can read and run in the repo. Apply every
one of the seven signs, the staging/doctrine/test-quality checks, and the
exact return format below. Be blunt; every finding carries a file:line.

Verify before you assert: check any claim about lint reachability ("this lint
fires"), test-only exemptions, dependency closures, build graphs, counts, or
"this regresses X" before asserting it -- run the relevant toolchain command
or grep; you have the toolchain for exactly this. When a needed check fails
to run in this environment (missing env vars, blocked network), mark that
finding PROVISIONAL ("needs a toolchain run") rather than a REJECT.

The criteria follow, then (if provided) the worker's close-out, then the diff.

----- REVIEW CRITERIA (adversarial-reviewer rubric) -----
EOF
else
read -r -d '' ADAPTER <<'EOF' || true
You are an external adversarial reviewer. The diff under review is included
verbatim at the end of this message. You also have read-only access to the
repository (cwd is the repo under review): use it to grep for prior art, read
the CLAUDE.md settled decisions, and inspect seam tests -- exactly the
corroboration the criteria call for. Claude teammate transcripts are outside
your reach here; wherever the criteria say to confirm a finding via a
teammate's transcript, reason instead from the diff plus what you can read in
the repo. Apply every one of the seven signs, the staging/doctrine/
test-quality checks, and the exact return format below. Be blunt; every
finding carries a file:line.

Verify before you assert: you run read-only, without compiling or running
lints or tests. Check any claim about dependency closures, build graphs,
counts, or "this regresses X" with the non-building tools you have
(dependency-graph queries, grep, reading lint config and lockfiles) before
asserting it. For a lint-reachability, "this lint fires", or test-only-
exemption claim that would need a lint or test run to confirm, mark that
finding PROVISIONAL ("needs a toolchain run") rather than a REJECT.

The criteria follow, then (if provided) the worker's close-out, then the diff.

----- REVIEW CRITERIA (adversarial-reviewer rubric) -----
EOF
fi

CLOSEOUT_BLOCK=""
if [ -n "$CLOSEOUT_IN" ]; then
  CLOSEOUT_BLOCK="
----- WORKER CLOSE-OUT REPORT -----
This is the implementer's own report. Run the CLAIMS CROSS-CHECK: for every
load-bearing claim (a count, a 'verified', an 'already exists', a 'byte-identical'),
confirm it against the diff and the repo. Mark each verified | partial | unverified.

$(cat "$CLOSEOUT_IN")
"
fi

PROMPT="$ADAPTER
$RUBRIC_BODY
$CLOSEOUT_BLOCK
----- DIFF UNDER REVIEW ($TARGET_DESC, tag=$TAG) -----
\`\`\`diff
$DIFF
\`\`\`"

declare -a EXTRA_FLAGS=()
[ -n "$MODEL" ] && EXTRA_FLAGS+=(--model "$MODEL")
[ -n "$EFFORT" ] && EXTRA_FLAGS+=(-c "model_reasoning_effort=$EFFORT")
# Warm shared build cache (Rust): grant the cargo target dir as a writable
# root so lint/test runs in the worktree do not cold-build from scratch.
if [ "$SANDBOX" = "workspace-write" ] && [ -n "${CARGO_TARGET_DIR:-}" ]; then
  EXTRA_FLAGS+=(-c "sandbox_workspace_write.writable_roots=[\"$CARGO_TARGET_DIR\"]")
fi

echo "codex-review: reviewing $TARGET_DESC in $REVIEW_DIR (tag=$TAG, sandbox=$SANDBOX, $(printf '%s' "$DIFF" | wc -l) diff lines${EFFORT:+, effort=$EFFORT}${CLOSEOUT_IN:+, +closeout})" >&2

# Prompt via stdin ('-') to dodge ARG_MAX on large diffs. Verbose run -> log;
# clean report -> closeout via -o. The sandbox bounds what Codex can touch:
# read-only = cannot edit; workspace-write = the disposable worktree only.
printf '%s' "$PROMPT" | codex exec \
    -s "$SANDBOX" \
    -C "$REVIEW_DIR" \
    "${EXTRA_FLAGS[@]}" \
    -o "$CLOSEOUT" \
    - >"$LOG" 2>&1 || {
  status=$?
  echo "codex-review: FAILED (exit $status). See $LOG" >&2
  exit $status
}

echo "codex-review: complete -> $CLOSEOUT  (full run: $LOG)"
