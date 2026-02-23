# CC-Optimizer

Central hub for Claude Code optimization. Mirrors the official documentation, provides a battle-tested optimization playbook, and bootstraps new machines with safe defaults.

## Quick Start

```bash
git clone https://github.com/JvKuechen/CC-Optimizer.git
cd CC-Optimizer

# Set git to use LF line endings (recommended for Windows -- CRLF breaks hooks/scripts)
git config --global core.autocrlf false
git config --global core.eol lf

# Clone wiki repo and install pre-push hook
python scripts/setup.py

# Deploy global permissions, guardrail hook, and notification sounds to ~/.claude/
python templates/deploy-user-settings.py
```

Then open Claude Code in this directory and run `/sync-docs` to fetch the latest documentation. Optionally install plugins with `/plugin`.

## What You Get

| What | Where | Purpose |
|------|-------|---------|
| Global permissions | `~/.claude/settings.json` | Pre-allows ~75 safe commands so Claude stops asking for approval on `ls` and `git status` |
| Guardrail hook | `~/.claude/hooks/guardrail.py` | Blocks destructive commands (`rm -rf /`, force push, `DROP DATABASE`) before they execute |
| Notification hook | `~/.claude/settings.json` | Audio alert when Claude needs your input |
| Optimization playbook | `playbook/` | Step-by-step checklist for bringing any project up to Claude Code best practices |
| 16 reusable patterns | `playbook/patterns/` | Proven techniques from 22+ workspace audits |
| Doc mirror | `docs/en/` (after sync) | 56 pages from code.claude.com, searchable offline |

## Configuration

This repo uses gitignored JSON configs for personal settings. Copy the example files to get started:

```bash
cp configs/user-config.example.json configs/user-config.json
cp configs/projects.example.json configs/projects.json
```

Edit them with your own values (remote URLs, project lists, etc.). See the example files for documentation on each field.

## Using This Repo

| Task | Command |
|------|---------|
| Sync official docs | `/sync-docs` |
| Optimize a project | `/optimize-workspace C:/path/to/project` |
| Bootstrap a new project | `/init-workspace C:/path/to/project` |
| Update playbook after sync | `/update-playbook` |

## Further Reading

See the [wiki](https://github.com/JvKuechen/CC-Optimizer/wiki) for detailed guides:

- [Getting Started](https://github.com/JvKuechen/CC-Optimizer/wiki/Getting-Started) -- full setup walkthrough
- [Repository Structure](https://github.com/JvKuechen/CC-Optimizer/wiki/Repository-Structure) -- what each directory does
- [Optimizing Workspaces](https://github.com/JvKuechen/CC-Optimizer/wiki/Optimizing-Workspaces) -- the optimization workflow
- [Skills Reference](https://github.com/JvKuechen/CC-Optimizer/wiki/Skills-Reference) -- available slash commands
- [Patterns Catalog](https://github.com/JvKuechen/CC-Optimizer/wiki/Patterns-Catalog) -- reusable optimization patterns
