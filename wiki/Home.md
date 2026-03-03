# CC-Optimizer

A workspace for maintaining Claude Code documentation and optimizing Claude Code workspaces across your projects.

## What This Repo Does

1. **Mirrors Claude Code docs** locally from [code.claude.com/docs](https://code.claude.com/docs) for offline reference
2. **Provides a playbook** of optimization patterns distilled from the official docs
3. **Bootstraps new machines** with global permissions, guardrail hooks, and plugins
4. **Optimizes other workspaces** via the `/optimize-workspace` skill

## Quick Links

| Page | Description |
|------|-------------|
| [Getting Started](Getting-Started) | Clone, bootstrap, and start using Claude Code |
| [Repository Structure](Repository-Structure) | What each directory and file does |
| [Optimizing Workspaces](Optimizing-Workspaces) | How to analyze and optimize a Claude Code project |
| [Skills Reference](Skills-Reference) | Available slash commands and when to use them |
| [Patterns Catalog](Patterns-Catalog) | Reusable optimization patterns from 24+ workspace audits |
| [Health Check Standard](Health-Check-Standard) | Cross-workspace health monitoring spec and integration pattern |

## Key Files in the Repo

- **`CLAUDE.md`** - Main workspace instructions (read by Claude every session)
- **`playbook/optimization-checklist.md`** - The actionable optimization playbook
- **`templates/deploy-user-settings.py`** - Machine bootstrap script
- **`playbook/patterns.md`** - Index of reusable optimization patterns
