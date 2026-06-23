# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Purpose

This is a **Codex Optimizer** workspace. It maintains a local mirror of the Codex documentation and uses it to optimize other Codex workspaces. Assumes access to Opus, Sonnet, and Haiku models.

## Platform

**Windows 11 only.** See `.Codex/rules/windows-shell.md` for mandatory shell rules. Key points: always use forward slashes in Bash, redirect to `/dev/null` rather than `nul`, call `python` (Windows has no `python3`), and always quote paths.

## Core Philosophy

**LLMs are mortar, scripts are bricks.** Prefer deterministic scripts and hardcoded workflows for reliable operations. Reserve LLM reasoning for decisions that genuinely require judgment.

## Working Posture

Optimization is judgment work. Push back when an audit finding, a pattern choice, or a user request looks wrong — flag it instead of applying it silently. When you get something wrong, correct it in one line and move on.

## Post-Clone Setup

IMPORTANT: Run `python scripts/setup.py` after cloning. This creates workspace directories, pins Codex to the stable release channel, installs git hooks, and (on Linux/WSL) ensures a bare `python` resolves via `python-is-python3` and the GitHub CLI (`gh`) is installed (auth is interactive: `gh auth login`). Wiki sync to GitHub/Gitea wikis is handled by CI workflows (no local setup needed). The script is idempotent.

## Workflow

1. **Sync docs** -- Run `python scripts/sync-docs.py` to fetch updated docs from code.Codex.com/docs. Run before optimization work.
2. **Follow the playbook** at `playbook/optimization-checklist.md` -- Distilled from the docs into an actionable checklist. This is the primary reference during optimization (not raw docs).
3. **`/update-playbook`** -- After a doc sync shows changes, reviews what changed and updates the playbook.
4. **`/init-workspace [name or path]`** -- Bootstraps a new workspace. With a name only, creates under `WS/`. With a path, initializes in place.
5. **`/optimize-workspace [name or path]`** -- Analyzes and optimizes a workspace. Can target nested workspaces by name or external paths. Offers to clone external projects into `WS/` first.

## Key Directories

- `WS/` -- Nested workspace clones (flat layout). Gitignored. Each project has its own .git. Use explicit Grep paths since rg skips gitignored dirs.
- `docs/en/` -- Local mirror of the English doc pages (raw markdown from code.Codex.com)
- `docs/manifest.json` -- Tracks lastmod timestamps per page for incremental sync
- `docs/plugin-marketplace-reference.md` -- Internal reference on plugin system and demo marketplace
- `playbook/` -- Actionable optimization checklist distilled from docs
- `playbook/patterns.md` -- Toolbelt: reusable patterns distilled from workspace audits
- `wiki/` -- GitHub/Gitea wiki content (tracked by main repo, synced to wiki remotes via CI on push to main). Searchable with Grep.
- `scripts/setup.py` -- Post-clone setup: creates workspace directories, installs git hooks
- `playbook/patterns/` -- Individual pattern files (current-state-capsule, gate-pattern, etc.)
- `findings/` -- Per-workspace audit reports (gitignored, temporary)
- `templates/` -- Reusable config: `user-settings.json`, `hooks/guardrail.py`, `deploy-user-settings.py`
- `.Codex/rules/` -- Path-scoped rules for this workspace
- `.Codex/skills/` -- optimize-workspace, init-workspace, update-playbook
- `.Codex/agents/` -- docs-reference (haiku, fast lookup), workspace-analyzer (sonnet, read-only audit)

## Machine Setup (once per computer)

Run `python templates/deploy-user-settings.py` to deploy to `~/.Codex/`:
- **Global permissions** (`settings.json`): Pre-allows ~75 safe commands across all workspaces
- **Guardrail hook** (`hooks/guardrail.py`): PreToolUse hook that blocks destructive Bash commands before execution
- **Notification hook**: Plays two tones when Codex needs input (permission prompt or idle 60s+)

**Parallel work needs no special machine setup.** The default fan-out model is background Agent-tool subagents spawned with `isolation: "worktree"`: each gets its own worktree from local `HEAD` and runs without moving the lead's checkout -- no tmux, no `cmux`, no `teammateMode`. A completion notification re-invokes the lead (survives compaction). See `templates/rules/coordination.md` for the full pattern.

**Optional -- agent-team mode** (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`): the multi-teammate team UI is a separate model most workflows do not need. There, run the lead in tmux (`teammateMode: "tmux"`) so an in-process teammate's `EnterWorktree` does not drag the lead; details + teardown quirks live in the `agent-teams-worktree-isolation` memory.

Then install recommended plugins (interactive-mode slash commands -- run inside a Codex session):
```
/plugin marketplace add anthropics/Codex
/plugin install frontend-design@Codex-plugins
/plugin install feature-dev@Codex-plugins
/plugin install security-guidance@Codex-plugins
/plugin install commit-commands@Codex-plugins
/plugin install code-review@Codex-plugins
```

The **fix-line-endings hook** (PostToolUse on Write|Edit) converts CRLF to LF immediately after every file write. The Write tool produces CRLF on Windows regardless of AGENTS.md instructions or git config -- this hook is the only reliable fix. Skips binary files and CRLF-required types (.bat, .cmd, .ps1, .psm1, .psd1).

The guardrail is a deterministic Python script (zero tokens, can't be reasoned around). It blocks:
- Docker data destruction (volume rm/prune, system prune, compose down -v)
- Broad filesystem deletion (rm -rf on root/home/C:, rmdir /s /q, del /s /q)
- Windows hazards (format, diskpart)
- Git destruction (force push, hard reset, clean -f)
- Database destruction (DROP DATABASE/SCHEMA)

Two PreToolUse **rewriter hooks** fix Windows-hostile constructs deterministically instead of blocking (which would force a retry). `shell-rewrite.py` rewrites `> nul` to `/dev/null` and `python3` to `python` in Bash commands. `ascii-normalize.py` transliterates non-ASCII typography to ASCII in source files, and blocks writes whose non-ASCII has no ASCII mapping (use a Bash heredoc for those). Both no-op on WSL/Linux.

This follows documented best practice: hooks-guide.md lists "Custom permissions: Block modifications to production files or sensitive directories" as a primary use case, and best-practices.md states hooks are "deterministic and guarantee the action happens" unlike advisory AGENTS.md instructions.

## The #1 Optimization Target

**Permission friction** is the biggest productivity blocker in new workspaces. Codex stops and waits for approval on basic commands like `ls`, `curl`, `git status`. Fix this FIRST by creating `.Codex/settings.json` with pre-allowed commands for the project's stack. The global permissions from machine setup handle most common commands; project settings add stack-specific ones.

## Permission Rule Syntax Quick Reference

```
Bash(npm run *)     — wildcard with space = word boundary
Bash(npm*)          — no space = prefix match (matches npmx too)
Read(.env.*)        — file pattern
Read(./secrets/**)  — recursive directory
```

Evaluation: deny always wins. Order: deny → ask → allow.

Settings precedence: managed > CLI args > local > project > user.

## AGENTS.md Authoring Rules

When writing AGENTS.md for other workspaces:
- Target under 200 lines per AGENTS.md file. Every line must pass: "Would removing this cause mistakes?"
- Use `@path` imports for existing docs (README, package.json) — reference, single-source
- Move detailed reference to `.Codex/skills/` (loaded on-demand, not every request)
- Use `.Codex/rules/` with `paths:` frontmatter for file-pattern-scoped conventions
- Use IMPORTANT / YOU MUST for critical rules Codex tends to ignore
- Phrase rules as positive targets; when an anti-pattern must be shown, label it `Rejected:` followed by the anti-pattern rather than writing a `never`/`don't` instruction
- Rejected from AGENTS.md: file-by-file descriptions, generic practices, tutorials, frequently-changing info

## Feature Selection Guide

| Need | Use | Why |
|------|-----|-----|
| Always-on conventions | AGENTS.md | Loaded every request (keep small) |
| Path-scoped conventions | .Codex/rules/ | Loaded only when editing matching files |
| On-demand workflows | .Codex/skills/ | Loaded when invoked, not every request |
| Deterministic automation | Hooks | Shell scripts, zero token cost, guaranteed |
| Isolated specialists | .Codex/agents/ | Custom tools/model, separate context |
| External services | MCP (.mcp.json) | Databases, APIs, GitHub |

## Workspace Consolidation

Active workspaces live as nested clones under `WS/` in this repo (flat layout, no org subfolders). Each nested workspace keeps its own `.git` and remotes. The `WS/` directory is gitignored -- nothing inside is committed to the optimizer repo. External paths still work for in-place optimization.

## Coordination

Multi-thread / multi-workspace coordination uses the protocol at `~/.Codex/rules/coordination.md` (deployed via `templates/deploy-user-settings.py`). Vocabulary: main thread = coordinator, subthread = focused executor, bounty board = in-chat cross-thread task state, close-out report = structured subthread return.

The bounty board is an in-chat artifact, reconstructed each session from `git log` + `capsule.toml`, and lives only in conversation context (a persisted board goes stale once its thread closes). Start a main-thread session by pasting `templates/main-thread-kickoff.md`; spawn subthreads using the brief template at `templates/subthread-brief.md` (customize each per task before pasting). `capsule.toml` (gitignored) is the only persistent local tracker. Thread-local IDs (`T<n>`, `D-*`, `#<n>`) live in `capsule.toml` and chat only — tracked source, docs, and rules use commit hashes or descriptive names instead.

## Public Repo Commit Workflow

This repo has a `.public-repo` marker. The pre-commit hook blocks direct `git commit`. YOU MUST follow this workflow:

1. Review staged diff: `git diff --cached`
2. Verify no hostnames, credentials, usernames, IPs, or environment-specific details
3. Commit using: `scripts/verified-commit.sh -m "message"`

Environment-specific content goes in gitignored files (e.g., `*-environments.md`). The tracked versions contain only generalized patterns. When creating new design docs, split into generic (tracked) and specific (gitignored) from the start.

## Public Repo Push Workflow

On repos with a `.public-repo` marker, a PreToolUse hook (`push-review.py`) intercepts `git push` commands. The hook swaps the push command with `scripts/push-review.py`, which outputs a consolidated diff review as Bash output. IMPORTANT: The Bash output is truncated in the UI. YOU MUST re-present the COMPLETE Bash output as markdown -- every section, every line of the diff, nothing omitted. Use ` ```diff ` fencing for syntax coloring. Do NOT run git push again -- the user will execute the push via the `!` command shown at the end of the review.

## Gotchas

- **Nested workspace search**: `WS/` is gitignored, so `rg` (Grep) from root skips it. Use explicit paths: `Grep(pattern, path="WS/{Project}")`. Glob DOES find files in gitignored dirs. Read/Edit/Write work on any path. Note: `wiki/` is tracked and IS included in Grep searches from root.
- **Co-Authored-By trailer**: Codex's system prompt adds `Co-Authored-By: Codex <noreply@anthropic.com>` to commits. GitHub parses this into ghost author avatars with broken names. Two layers suppress it: `attribution.commit: ""` in user settings tells Codex not to append it, and the commit-msg hook (`scripts/setup.py`) strips it as a fallback if the setting is renamed.
- CLI auto-generates deprecated colon syntax `Bash(cmd:*)` in settings.local.json when user clicks "always allow." Functional but inconsistent with docs which show `Bash(cmd *)`. Accept as-is.
- Moving a workspace folder orphans `/resume` session history. Fix by renaming the directory under `~/.Codex/projects/` to match the new path encoding (replace `\` with `-`, colon with `-`).
- `[console]::beep` has no volume parameter. Pitch and duration are the only controls.
- **nul file cleanup**: Bad `> nul` redirects in Git Bash create literal `nul` files that `rm`, `del`, and Explorer cannot delete. Use `python scripts/delete-nul-files.py <path>` (Win32 DeleteFileW API with `\\?\` prefix). Common in unoptimized workspaces.
- **Hidden .git after copy/move**: `cp -r`, `shutil.move()`, and `shutil.copytree()` strip the Windows hidden attribute from `.git` directories. Always run `attrib +H "<dest>/.git"` after copying or moving a repo. The `fan-out/migrate.py` script handles this automatically.
- Windows NTFS is case-insensitive but case-preserving. `mkdir work` then `ls` may show `Work` if the directory pre-existed with that casing.
- **Wiki sync**: CI workflows (`.github/workflows/wiki-sync.yml`, `.gitea/workflows/wiki-sync.yml`) push `wiki/` content to both remotes on push to main. Requires `WIKI_TOKEN` secret on both platforms (org-level on Gitea), plus `INTERNAL_CA_PEM` on Gitea.
- **MCP Python servers on Windows**: `"command": "python"` in `.mcp.json` fails because Node.js `spawn()` cannot resolve the Windows Store Python alias. Wrap with cmd: `"command": "cmd", "args": ["/c", "python", "-m", "package_name"]`. Also check that the package has a `__main__.py` -- some (e.g., `mssql_mcp_server` 0.1.2) ship without one, requiring a manual shim in site-packages.

## Scope

This workspace handles **Codex CLI** optimization only.

## Doc Pages Quick Index

For optimization: best-practices, memory, settings, features-overview, model-config, output-styles, context-window, costs, env-vars
For extensibility: skills, hooks, hooks-guide, sub-agents, plugins, plugins-reference, mcp, plugin-marketplaces, plugin-dependencies, discover-plugins, tools-reference, commands, plugin-marketplace-reference (internal)
For workflows: common-workflows, cli-reference, interactive-mode, authentication, scheduled-tasks, routines, remote-control, code-review, ultraplan, ultrareview, voice-dictation
For permissions: permissions, permission-modes, auto-mode-config, sandboxing, server-managed-settings
For UI/terminal: fullscreen, statusline, terminal-config, keybindings, deep-links, sessions
For team features: agent-teams, channels, channels-reference, champion-kit, communications-kit
For diagnostics: debug-your-config, troubleshoot-install, troubleshooting, errors, glossary, how-Codex-works, Codex-directory, whats-new, changelog
For new features: checkpointing, fast-mode, analytics, computer-use
For infrastructure: headless, github-actions, github-enterprise-server, gitlab-ci-cd, monitoring-usage, network-config, devcontainer, platforms, setup, third-party-integrations
For provider/cloud: amazon-bedrock, google-vertex-ai, microsoft-foundry, llm-gateway
For surfaces: desktop, desktop-quickstart, desktop-scheduled-tasks, vs-code, jetbrains, chrome, slack, Codex-on-the-web, web-quickstart
For compliance: legal-and-compliance, zero-data-retention, data-usage, security
