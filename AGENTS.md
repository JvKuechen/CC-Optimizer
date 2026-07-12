# AGENTS.md

This file orients Codex when working in this repository.

## What this repository is

This is a **Claude Code optimizer** workspace. It maintains a local mirror of
the Claude Code documentation (`docs/en/`, fetched from code.claude.com/docs)
and distills it into a playbook used to optimize other Claude Code workspaces.
The primary agent surface is Claude Code; its instructions live in `CLAUDE.md`
and `.claude/`.

**Codex's role here** is cross-vendor: adversarial review legs invoked via
`scripts/codex-review.sh` (the loop kit's review gate), plus any task the user
hands Codex directly. Codex-specific config lives under `.codex/` (agents,
hooks) -- that is the Codex parallel to `.claude/`, kept in lockstep where the
two overlap.

## Platform

**Windows 11 only.** The shell rules at `.claude/rules/windows-shell.md` apply
to any shell or hook code you write: forward slashes in Bash paths, redirect to
`/dev/null` (a literal `nul` file resists deletion), call `python` (Windows has
no `python3`), quote all paths, plain ASCII in code (no emojis, no Unicode
arrows or dashes), LF line endings.

## Core philosophy

**LLMs are mortar, scripts are bricks.** Prefer deterministic scripts and
hardcoded workflows for reliable operations. Reserve LLM reasoning for
decisions that genuinely require judgment.

Optimization is judgment work. Push back when an audit finding, a pattern
choice, or a user request looks wrong -- flag it instead of applying it
silently. When you get something wrong, correct it in one line and move on.

## Key directories

- `docs/en/` -- local mirror of the **Claude Code** doc pages (raw markdown)
- `playbook/` -- optimization checklist + `patterns/` (reusable patterns
  distilled from workspace audits)
- `templates/` -- reusable config deployed into other workspaces: hooks,
  agents, the loop kit (`templates/loop/`), the Codex review leg
  (`templates/codex/`)
- `scripts/` -- deterministic tooling; `codex-review.sh` is the deployed
  review-leg entry point
- `wiki/` -- tracked wiki content, synced to GitHub/Gitea wikis by CI
- `WS/` -- nested workspace clones, gitignored, each with its own `.git`
- `findings/` -- per-audit reports and review outputs, gitignored
- `.claude/` -- Claude Code rules, skills, agents; `.codex/` -- Codex agents
  and hooks

## Review-leg contract

When running as the adversarial reviewer (via `codex-review.sh`), the rubric
arrives in the prompt -- apply it as given. End every review report with a
single terminal line so the deterministic gate can parse the outcome:

```
VERDICT: ACCEPT | CONDITIONAL | REJECT
```

The reviewer role is the one surface licensed for negative framing and
`Rejected:` labels; everywhere else, phrase guidance as positive targets.

## Commit workflow (public repo)

This repo has a `.public-repo` marker; the pre-commit hook blocks direct
`git commit`. **Follow this workflow:**

1. Review the staged diff: `git diff --cached`
2. Verify no hostnames, credentials, usernames, IPs, or environment-specific
   details
3. Commit using: `scripts/verified-commit.sh -m "message"`

Environment-specific content goes in gitignored files (e.g.
`*-environments.md`); tracked versions carry only generalized patterns.
Leave `git push` to the user.

## Gotchas

- `WS/` and `findings/` are gitignored, so ripgrep skips them from the root --
  search them with explicit paths.
- Git for Windows must keep `core.autocrlf=false`; the repo's `.gitattributes`
  enforces LF. Write files with LF endings.
- Windows NTFS is case-insensitive but case-preserving; path casing in
  citations matters on WSL.
- `cp -r` and Python `shutil` copies strip the hidden attribute from `.git`
  directories; run `attrib +H "<dest>/.git"` after copying a repo.
