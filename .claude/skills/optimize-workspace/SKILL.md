---
name: optimize-workspace
description: Analyze and optimize another Claude Code workspace's configuration
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task, WebFetch, AskUserQuestion
argument-hint: "[path-to-workspace]"
---

Optimize the Claude Code workspace at `$ARGUMENTS`.

## Resolve Target

1. **If `$ARGUMENTS` is a path**: Use it directly.
2. **If `$ARGUMENTS` is a project name** (no path separators): Look for it under `WS/` in the CC-Optimizer repo.
3. **If no arguments**: List projects under `WS/` and ask the user to pick one, or provide a path.

## Nested vs External Decision

If the target is NOT already under `WS/`, ask the user:

> Optimize in place, or copy into WS/ first?

- **In place**: Proceed at the target's current location (existing behavior).
- **Copy into WS**: Copy the local project into `WS/{project}/` (preserves gitignored files and local state), then re-hide `.git` (`attrib +H "<target>/.git"`), then migrate session history with `python scripts/migrate-sessions.py`, then optimize the copy.

## Grep Workaround for Nested Workspaces

When the target is under `WS/` (gitignored), `rg` from the CC-Optimizer root will NOT search into it. Always use an explicit path:

```
Grep(pattern, path="WS/{Project}")
```

Glob DOES discover files in gitignored directories. Read/Edit/Write work on any path.

## Pre-Optimization

1. **Smoke test** -- IMPORTANT: Before changing anything, verify the project works. Run its build, tests, or main entry point. Record what passes. If something is functional before optimization, it MUST be functional after.

2. **Git safety** -- If the target is not a git repo, run `git init && git add -A && git commit -m "Pre-optimization snapshot"`. If it is, ensure working tree is clean (commit or stash pending changes).

3. **Read findings** -- Check `findings/` in this workspace for an existing audit report on the target. If found, use it as the starting point instead of re-auditing.

4. **Follow the playbook** -- Use `playbook/optimization-checklist.md` as the authoritative checklist. Do NOT consult raw docs unless the playbook is insufficient.

## Analysis Phase (Playbook Phases 1-1.5)

4. **Identify stack** -- Language, framework, build system, test runner, linter, deployment.

5. **Check existing Claude config** -- CLAUDE.md, .claude/, .mcp.json, hooks, other AI configs.

6. **Select patterns** -- Review `playbook/patterns.md` toolbelt. Check each pattern's "When" section against this workspace. Record applicable patterns.

7. **Per-project feature decisions** -- MCP, LSP, Chrome, sandboxing, fan-out.

## Implementation Phase (Playbook Phases 2-8)

8. **Fix permissions** (Phase 2) -- Create `.claude/settings.json` with `$schema` reference, stack-specific allows and deny rules. Use explicit git subcommands, not `Bash(git *)`. Use `//path` for absolute paths (not `/path`). Consider `dontAsk` mode for locked-down workflows.

9. **Optimize CLAUDE.md** (Phase 3) -- Under 500 lines. Add gotchas, business context. Apply selected patterns (current-state-capsule, blocked-task-tracking, etc.). Use `@path` imports.

10. **Add rules** (Phase 4) -- Always deploy:
    - `.claude/rules/context-handoff.md` (copy from optimizer workspace)
    - `.claude/rules/windows-shell.md` (copy from optimizer workspace, for Windows targets)
    - Project-specific path-scoped rules as needed.

11. **Add skills** (Phase 5) -- For repeatable workflows.

12. **Add subagents** (Phase 6) -- For isolated specialists.

13. **Add hooks** (Phase 7) -- Three types: `command` (deterministic, zero tokens), `prompt` (LLM evaluation), `agent` (multi-turn verification). Check for sandbox candidates (`/sandbox`).

14. **Public repo lock** (Phase 7.5) -- Check if any remote is public:
    ```bash
    git -C "<target>" remote -v
    ```
    - `github.com`, `gitlab.com`, other public hosts = potentially public.
    - Private IPs, `.local` domains, LAN-only Gitea = private. Skip.
    - If public remote found and no `.public-repo` marker exists, ask the user if the repo is public.
    - If yes: create `.public-repo` marker, install pre-commit hook (blocks `git commit` unless `PUBLIC_REPO_VERIFIED=1`), install commit-msg hook (strips Co-Authored-By). Add `scripts/verified-commit.sh` wrapper. Add `Bash(scripts/verified-commit.sh *)` to `.claude/settings.json` allow list. Document the workflow in CLAUDE.md.
    - See CC-Optimizer's `scripts/setup.py` for the hook content (`PRE_COMMIT_HOOK`, `COMMIT_MSG_HOOK`).

15. **Windows compat** (Phase 8) -- Check for nul files, tmpclaude files, Unix-only constructs.

## Post-Optimization

16. **Verify** -- Re-run the same smoke test from step 1. If anything broke, fix it before committing. Optimization must not regress functionality.

17. **Commit** -- `git add -A && git commit -m "Claude Code optimization"`. User can `git diff HEAD~1` to review or `git revert HEAD` to undo.

18. **Report** -- Summarize all changes and rationale. Note anything needing user customization.

19. **Clean up optimizer workspace** -- Check `CC-Optimizer/.claude/settings.local.json` for stale entries accumulated from "always allow" clicks during this optimization. Remove any that are already covered by project or global settings. Keep only `WebSearch`.

## Key Principles
- Follow the playbook, not raw docs
- LLMs are mortar, scripts are bricks
- Permission friction is the #1 blocker -- fix it first
- CLAUDE.md under 500 lines
- Credential hygiene check is always applicable
- Git safety net before and after
- NEVER regress functionality -- smoke test before and after
