# Skills Reference

Skills are on-demand workflows invoked with slash commands. They're only loaded when called, keeping the per-request token cost low.

## Available Skills

### /sync-docs

**Purpose:** Fetch updated Claude Code documentation from code.claude.com

**When to use:** Before optimization work, or when you suspect docs have changed.

**What it does:**
- Fetches the sitemap XML to discover pages and their lastmod timestamps
- Only downloads pages that are new or have changed (incremental sync)
- Updates `docs/manifest.json` with new timestamps
- Currently tracks 56 English documentation pages

**Defined in:** `.claude/skills/sync-docs/SKILL.md`

---

### /optimize-workspace [name or path]

**Purpose:** Analyze and optimize another Claude Code workspace

**When to use:** When you want to bring a project up to Claude Code best practices.

**What it does:**
1. Resolves the target -- by project name (looks under `WS/`), by path, or interactively
2. For external projects, offers to copy into `WS/` first (preserves local state, migrates session history)
3. Smoke tests the target project first
4. Ensures git safety (clean working tree or snapshot)
5. Follows `playbook/optimization-checklist.md` phases 1-8
6. Fixes permissions, creates/improves CLAUDE.md, adds rules/skills/hooks
7. Re-runs smoke test to verify nothing broke
8. Commits changes with a single "Claude Code optimization" commit

**Defined in:** `.claude/skills/optimize-workspace/SKILL.md`

---

### /init-workspace [name or path]

**Purpose:** Bootstrap a new Claude Code workspace or import an existing project

**When to use:** When starting a new project, adding Claude Code to a project for the first time, or moving a project into the nested workspace structure.

**What it does:**
- With a **project name only**: creates under `WS/{name}/`
- With a **path**: initializes in place at that path
- **Importing**: copies local project (preserving gitignored files), migrates `/resume` session history via `scripts/migrate-sessions.py`
- Detects the tech stack (or asks if empty directory)
- Creates CLAUDE.md, .claude/settings.json, .gitignore
- Deploys standard rules (context-handoff, windows-shell)
- Does NOT add skills, hooks, agents, or MCP (use /optimize-workspace for that)

**Defined in:** `.claude/skills/init-workspace/SKILL.md`

---

### /update-playbook

**Purpose:** Refresh the optimization playbook after a docs sync

**When to use:** After `/sync-docs` shows updated pages.

**What it does:**
- Compares doc lastmod dates against the playbook's baseline
- Reads changed pages and identifies new features, syntax changes, deprecations
- Updates `playbook/optimization-checklist.md` and related files

**Defined in:** `.claude/skills/update-playbook/SKILL.md`

## Utility Scripts

### scripts/migrate-sessions.py

**Purpose:** Migrate `/resume` session history when a workspace moves to a new path.

**Usage:**
```bash
# Single workspace
python scripts/migrate-sessions.py <old-path> <new-path>

# Parent move (migrates parent + all nested workspaces at once)
python scripts/migrate-sessions.py --parent <old-parent> <new-parent>

# Preview only
python scripts/migrate-sessions.py --dry-run --parent <old-parent> <new-parent>
```

Claude stores conversation history under `~/.claude/projects/` keyed by the encoded workspace path. When you move a workspace folder, `/resume` shows no history. This script renames the session directory to match the new path. The `--parent` flag handles bulk moves (e.g., moving CC-Optimizer itself migrates all nested workspace sessions in one pass).

### scripts/delete-nul-files.py

**Purpose:** Delete Windows `nul` files created by bad `> nul` redirects in Git Bash.

**Usage:**
```bash
python scripts/delete-nul-files.py <directory>   # Scan and delete
python scripts/delete-nul-files.py               # Scan current directory
```

On Windows, `nul` is a reserved device name. Git Bash doesn't translate `> nul` to `> /dev/null`, creating literal `nul` files that `rm`, `del`, and Explorer cannot delete. This script uses the Win32 `DeleteFileW` API with the `\\?\` extended-length path prefix to bypass the restriction. Common in unoptimized workspaces where CLAUDE.md doesn't have the "use `/dev/null`" rule.

### scripts/setup.py

**Purpose:** Post-clone workspace setup.

**Usage:**
```bash
python scripts/setup.py              # Normal setup
python scripts/setup.py --reconfigure # Re-prompt for org folder names
```

Sets up long path support, workspace directories, and git hooks (pre-commit, commit-msg, pre-push). Wiki sync is handled by CI workflows, not local hooks. Idempotent -- safe to run multiple times.
