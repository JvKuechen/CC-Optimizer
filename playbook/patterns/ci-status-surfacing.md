# CI-Status Surfacing

**Source:** FortrOS paradigm-comb initiative

## When

Any workspace with CI gates (GitHub Actions) where a failing workflow can sit red across
several pushes unnoticed. A gate nobody looks at protects nothing -- and the longer it's red,
the more changes pile up on top of a broken baseline. This surfaces CI failures *in the loop*,
deterministically, so a red gate is caught at the next session instead of N pushes later.

It found a real one on its first run: a `rustdoc` strict-doc gate that had been failing four
consecutive runs, completely separate from the clippy failure the team was actively fixing.

## How

`templates/hooks/ci-status.py` queries the default branch's recent workflow runs via the
GitHub CLI and emits an `additionalContext` summary of any workflow whose latest *completed*
run failed -- which workflow, the consecutive-failure streak, the commit, and when. It always
reflects the last **pushed** state (CI hasn't run on local unpushed merges), which is the
correct semantic: "before I integrate/push more, is the baseline red?"

**Wire it at the cadence breaks actually surface.** This is the decision that matters:
- **Merge gate (recommended for a long-running coordinator that delegates to subagents).** A
  `PreToolUse(Bash)` hook that fires only on `git merge`, so the coordinator sees a red baseline
  right as it goes to integrate the next branch -- the moment to *not* stack on red and to put a
  fix on the board. This matches the push cadence; SessionStart does not (a long-running session
  rarely restarts, so SessionStart-surfaced status goes stale).
  ```
  {"hooks": {"PreToolUse": [
    {"matcher": "Bash",
     "hooks": [{"type": "command",
                "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/ci-status.py\""}]}
  ]}}
  ```
- **SessionStart (for restart-heavy layouts).** Same hook, no matcher -- fits workspaces that
  start fresh sessions often.

The hook auto-detects the event (gates to `git merge` in `PreToolUse`, always checks in
`SessionStart`), so the wiring choice is the only difference.

Design choices that matter:
- **Quiet on green.** Emits nothing when every workflow is healthy -- the summary only ever
  means "something is red."
- **Graceful degradation.** No-ops silently if `gh` is absent/unauthed or there are no runs.
- **Streak count.** "4 consecutive" distinguishes a flake from a gate broken across pushes --
  the latter is the urgent signal.

Prerequisite: the GitHub CLI installed + authed (`gh auth login`, HTTPS). Fold the install into
post-clone setup (`scripts/setup.py` `setup_gh_cli()`) so it's present by default; auth is
interactive and stays a one-time manual step.

## Variants

- **On-demand check:** the same script as a `/ci-status` skill for a mid-session look.
- **Drill-in:** the summary points at `gh run view --log-failed` for the actual error; a
  variant can fetch and inline the failed-step tail.
- Pairs with [Gate Pattern](gate-pattern.md) (the gate this keeps honest) and
  [Push Review Gate](push-review-gate.md).
