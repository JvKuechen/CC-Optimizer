# Optimization Principles

When optimizing another Claude Code workspace, follow these rules:

## LLM as Mortar, Scripts as Bricks
- Prefer deterministic scripts and hardcoded workflows over LLM-driven operations
- Use hooks (shell scripts) for anything that should happen automatically and reliably
- Use skills to orchestrate scripts, not to replace them
- Reserve LLM reasoning for decisions that genuinely require judgment

## CLAUDE.md Authoring
- Target under 500 lines. Every line must pass: "Would removing this cause Claude to make mistakes?"
- Use `@path` imports to reference existing docs (README.md, package.json) rather than duplicating
- Move detailed reference material to `.claude/skills/` (loaded on-demand, not every request)
- Use `.claude/rules/` with `paths:` frontmatter for file-pattern-scoped rules
- Use IMPORTANT / YOU MUST for critical rules that Claude tends to ignore
- Never include: file-by-file descriptions, generic best practices, tutorials, frequently-changing info

## Permission Configuration
- The #1 blocker to productivity is permission friction for safe commands
- Always create `.claude/settings.json` with pre-allowed common tools for the project's stack
- Use `~/.claude/settings.json` (user scope) for globally safe commands (curl, ls, git read ops, etc.)
- Deny rules for: destructive git operations, sensitive files (.env, credentials, ssh keys)
- Permission rules use prefix matching: `Bash(npm run *)` matches `npm run test`, `npm run build`, etc.

## Feature Selection
- CLAUDE.md: Always-on conventions (loaded every request — keep small)
- Rules (.claude/rules/): Path-scoped conventions (loaded when editing matching files)
- Skills (.claude/skills/): On-demand workflows and reference material
- Hooks: Deterministic automation (lint on save, block dangerous commands, filter output)
- Subagents (.claude/agents/): Isolated specialists (code review, security audit, test analysis)
- MCP: External service connections (databases, APIs, GitHub)

## Cost Awareness
- Move verbose content from CLAUDE.md to skills (saves tokens every request)
- Use hooks to filter test output before Claude sees it (PreToolUse on Bash)
- Prefer haiku for subagents doing simple tasks (grep, triage)
- Use opus only for complex architectural decisions
