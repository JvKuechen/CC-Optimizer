# Optimizing Workspaces

## Overview

The primary workflow for optimizing a Claude Code workspace:

1. Ensure docs are up to date: `/sync-docs`
2. Import or target the workspace: `/init-workspace` to bring it into `WS/`, or use a path
3. Optimize: `/optimize-workspace <name or path>`
4. Follow the checklist in `playbook/optimization-checklist.md`

## Using /optimize-workspace

From a Claude Code session in the CC-Optimizer directory:

```
# By project name (looks under WS/)
/optimize-workspace MyProject

# By path (external project)
/optimize-workspace C:/Users/you/projects/MyProject

# No args (lists nested workspaces to pick from)
/optimize-workspace
```

When targeting an external project, the skill asks whether to optimize in place or copy into `WS/` first. Copying preserves gitignored files and local state, and migrates `/resume` session history.

This skill:
1. Resolves the target workspace
2. Smoke tests the project first
3. Ensures git safety (clean working tree or snapshot)
4. Follows `playbook/optimization-checklist.md` phases 1-8
5. Fixes permissions, creates/improves CLAUDE.md, adds rules/skills/hooks
6. Re-runs smoke test to verify nothing broke
7. Commits changes with a single "Claude Code optimization" commit

## The Optimization Checklist

The full checklist lives at `playbook/optimization-checklist.md` in the repo. Key sections:

1. **Pre-flight: Machine Setup** - Global permissions, guardrail, plugins (one-time)
2. **Permission Configuration** - The #1 productivity blocker to fix first
3. **CLAUDE.md Authoring** - Under 500 lines, @path imports, no duplication
4. **Rules and Skills** - Path-scoped conventions, on-demand workflows
5. **Hooks** - Deterministic automation (lint, format, guard)
6. **Sub-agents** - Isolated specialists for code review, security, testing
7. **MCP** - External service connections

## Priority Order

Always fix **permission friction first**. Claude stopping to ask approval for `ls` or `git status` is the single biggest time waster. Create `.claude/settings.json` with pre-allowed commands for the project's stack.

After permissions, the highest-value optimizations are:
1. CLAUDE.md (clear instructions prevent mistakes)
2. Path-scoped rules (reduce CLAUDE.md bloat)
3. Skills (move reference material out of always-on context)
4. Hooks (automate what shouldn't need LLM judgment)

## Patterns

See `playbook/patterns.md` for the index of reusable patterns discovered across workspace audits. Each pattern has its own file in `playbook/patterns/` with examples and usage guidance.

### Gitignored Search Reminder (Hook Pattern)

Claude Code's Grep uses ripgrep, which skips gitignored directories like `WS/`. For workspaces with gitignored content Claude needs to search, a PostToolUse hook on Grep can remind Claude to re-search with explicit paths. Note: `wiki/` is tracked by the main repo and included in searches automatically. See `playbook/patterns/gitignored-search-reminder.md`.
