# CC-Optimizer

Central hub for Claude Code optimization. Mirrors the official documentation, provides a battle-tested optimization playbook, and bootstraps new machines with safe defaults.

## Quick Start

```bash
git clone https://github.com/JvKuechen/CC-Optimizer.git
cd CC-Optimizer
git clone https://github.com/JvKuechen/CC-Optimizer.wiki.git wiki

# Set git to use LF line endings (Windows default is CRLF which breaks things)
git config --global core.autocrlf false
git config --global core.eol lf

# Clone wiki and install hooks
python scripts/setup.py

# Bootstrap your machine (deploys global permissions, guardrail hook, notifications)
python templates/deploy-user-settings.py

# Install plugins (interactive-mode slash commands -- run inside a Claude Code session)
# /plugin marketplace add anthropics/claude-code
# /plugin install frontend-design@claude-code-plugins
# /plugin install feature-dev@claude-code-plugins
# /plugin install security-guidance@claude-code-plugins
# /plugin install commit-commands@claude-code-plugins
# /plugin install code-review@claude-code-plugins
```

Then open Claude Code in this directory. Install plugins with `/plugin` and run `/sync-docs` to fetch the latest documentation.

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
