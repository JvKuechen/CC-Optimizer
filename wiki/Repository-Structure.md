# Repository Structure

## Directory Layout

```
CC-Optimizer/
├── CLAUDE.md                    # Workspace instructions (loaded every session)
├── .public-repo                 # Public repo marker (enables pre-commit hook)
├── .gitignore
├── .claude/
│   ├── settings.json            # Project-level permissions + hooks
│   ├── hooks/                   # Project-specific hook scripts
│   ├── rules/                   # Path-scoped conventions
│   │   ├── context-handoff.md   # Multi-session context protocol
│   │   ├── optimization-principles.md
│   │   ├── windows-shell.md     # Windows 11 shell rules
│   │   └── writing-settings.md  # Settings syntax reference
│   ├── skills/                  # On-demand workflows
│   │   ├── sync-docs/           # Fetch docs from code.claude.com
│   │   ├── optimize-workspace/  # Analyze and optimize a workspace
│   │   ├── init-workspace/      # Initialize or import a workspace
│   │   └── update-playbook/     # Review doc changes, update playbook
│   └── agents/                  # Specialized sub-agents
│       ├── docs-reference.md    # Haiku - fast doc lookup
│       └── workspace-analyzer.md # Sonnet - read-only audit
├── configs/
│   ├── user-config.example.json # Template (copy to user-config.json)
│   └── projects.example.json
├── docs/
│   ├── manifest.json            # Sync timestamps (tracked in git)
│   ├── plugin-marketplace-reference.md
│   └── en/                      # 56 doc pages (gitignored, fetched via /sync-docs)
├── playbook/
│   ├── optimization-checklist.md # Primary optimization reference
│   ├── cheatsheet.md            # Feature quick reference
│   ├── patterns.md              # Index of reusable patterns
│   ├── patterns/                # Individual pattern files
│   └── roadmap.md               # Optimization progress tracker
├── scripts/
│   ├── setup.py                 # Post-clone setup (workspaces, hooks)
│   ├── verified-commit.sh       # Commit wrapper for public repo (bypasses pre-commit lock)
│   ├── migrate-sessions.py      # Move /resume history when workspace path changes
│   └── delete-nul-files.py      # Remove undeletable 'nul' files (Win32 API)
├── templates/
│   ├── deploy-user-settings.py  # Machine bootstrap script
│   ├── user-settings.json       # Global permissions template
│   └── hooks/
│       └── guardrail.py         # Destructive command blocker
├── WS/                          # Nested workspace clones (gitignored)
│   └── {Project}/               # Each project has its own .git
├── findings/                    # Per-workspace audit reports (gitignored)
└── wiki/                        # Wiki content (tracked; synced to wikis via CI)
```

## What's Tracked vs Gitignored

| Path | Tracked? | Why |
|------|----------|-----|
| `WS/` | No | Nested workspace clones with their own git repos |
| `docs/en/` | No | Fetched on demand via `/sync-docs` - each user syncs their own |
| `docs/manifest.json` | Yes | Tracks lastmod timestamps for incremental sync |
| `configs/user-config.json` | No | User-specific settings (org folders, remotes, etc.) |
| `findings/` | No | Temporary audit reports, per-user |
| `wiki/` | Yes | Content tracked by main repo; synced to GitHub/Gitea wikis via CI on push |
| `.claude/settings.local.json` | No | User-specific permission overrides |

## Nested Workspaces

Active projects live under `WS/` in a flat layout (no org subfolders). Each project keeps its own `.git` and remotes.

**Search behavior**: `WS/` is gitignored, so `rg` (Grep) from the repo root skips it. Use explicit paths: `Grep(pattern, path="WS/{Project}")`. Glob does find files in gitignored directories. Read/Edit/Write work on any path. `wiki/` is tracked and included in Grep searches normally.

## Feature Selection Guide

This table (from `CLAUDE.md`) shows when to use which Claude Code feature:

| Need | Use | Why |
|------|-----|-----|
| Always-on conventions | `CLAUDE.md` | Loaded every request (keep small) |
| Path-scoped conventions | `.claude/rules/` | Loaded only when editing matching files |
| On-demand workflows | `.claude/skills/` | Loaded when invoked, not every request |
| Deterministic automation | Hooks | Shell scripts, zero token cost, guaranteed |
| Isolated specialists | `.claude/agents/` | Custom tools/model, separate context |
| External services | MCP (`.mcp.json`) | Databases, APIs, GitHub |
