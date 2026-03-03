# Getting Started

## Prerequisites

- [Claude Code CLI](https://code.claude.com/docs/setup) installed
- Git
- Windows 11

## 1. Clone the Repo

```bash
git clone https://github.com/JvKuechen/CC-Optimizer.git
cd CC-Optimizer

# Set git to use LF line endings (recommended for Windows -- CRLF breaks hooks/scripts)
git config --global core.autocrlf false
git config --global core.eol lf

# Set up workspaces and install git hooks
python scripts/setup.py
```

The setup script will:
- Enable git long path support (`core.longpaths`)
- Check the Windows LongPathsEnabled registry setting
- Create the `WS/` directory for nested workspaces
- Install git hooks (pre-commit, commit-msg, pre-push)

Wiki content in `wiki/` is tracked by the main repo and synced to GitHub/Gitea wikis automatically via CI workflows on push to main. No local wiki setup is needed.

## 2. Bootstrap Your Machine

This deploys global permissions, a guardrail hook, and notification sounds to `~/.claude/`:

```bash
python templates/deploy-user-settings.py
```

What gets deployed:

| File | Purpose |
|------|---------|
| `~/.claude/settings.json` | Pre-allows ~75 safe commands (ls, git status, curl, etc.) across all workspaces |
| `~/.claude/hooks/guardrail.py` | Blocks destructive commands (rm -rf /, force push, DROP DATABASE, etc.) |
| Notification hook | Audio alert when Claude needs your input |

See `templates/user-settings.json` in the repo for the full list of pre-allowed commands.

## 3. Install Plugins

Open Claude Code in the CC-Optimizer directory and run these slash commands:

```
/plugin marketplace add anthropics/claude-code
/plugin install frontend-design@claude-code-plugins
/plugin install feature-dev@claude-code-plugins
/plugin install security-guidance@claude-code-plugins
/plugin install commit-commands@claude-code-plugins
/plugin install code-review@claude-code-plugins
```

Or use `/plugin` to browse and install interactively.

## 4. Sync the Documentation

Open Claude Code in the CC-Optimizer directory and run:

```
/sync-docs
```

This fetches the latest Claude Code documentation from code.claude.com into `docs/en/`. The docs are gitignored (fetched on demand, not stored in the repo) so each user syncs their own copy.

## 5. Verify Everything Works

Start a Claude Code session in any project. You should:
- See no permission prompts for basic commands (ls, git status, etc.)
- Hear two tones when Claude asks for input
- Be able to run `/optimize-workspace .` to analyze the current workspace

## Public Repo Commit Workflow

This repo has a `.public-repo` marker file because it is published to GitHub. The pre-commit hook blocks direct `git commit` to prevent accidental leaks of hostnames, credentials, or environment-specific details.

**To commit changes:**

1. Stage your files: `git add <files>`
2. Review the diff: `git diff --cached`
3. Verify nothing environment-specific is staged (no hostnames, usernames, IPs, credentials)
4. Commit using the verified wrapper: `scripts/verified-commit.sh -m "your message"`

A Claude Code PreToolUse hook intercepts `git push` and presents a full consolidated diff for review before the push proceeds, giving the human a final chance to catch anything.

**Splitting generic vs specific content:** Design docs and configs that contain environment-specific details (hostnames, service names, SSH credentials) go in gitignored companion files. For example, the [Health Check Standard](Health-Check-Standard) lives in the wiki (generic spec), while `configs/health-check-environments.md` is gitignored (your specific setup). The `.gitignore` uses the pattern `configs/*-environments.md` to catch these.

**Removing the lock:** Delete `.public-repo` to disable the pre-commit check. This is an intentional action -- you accept responsibility for what gets pushed.

## Next Steps

- Read the [Optimizing Workspaces](Optimizing-Workspaces) guide to start improving projects
- Browse the [Patterns Catalog](Patterns-Catalog) for proven optimization techniques
- Check `playbook/optimization-checklist.md` for the full step-by-step checklist
