---
name: init-workspace
description: Bootstrap a new Claude Code workspace or import an existing one
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
argument-hint: "[project-name or path-to-workspace]"
---

Bootstrap a new Claude Code workspace, or import an existing project into the nested workspace structure.

## Resolve Target Path

Determine where the workspace will live based on `$ARGUMENTS`:

- **Absolute or relative path provided** (contains `/` or `\`): Use that path directly (existing external-path behavior).
- **Project name only** (no path separators): Read org folders from `configs/user-config.json` (key: `workspace_orgs`). Ask the user which org to use, then set target to `workspaces/{Org}/{project-name}/` inside the CC-Optimizer repo. If no config exists, ask the user to run `python scripts/setup.py` first.
- **No arguments**: Ask for project name and org folder (from config), then set target as above.

## Importing an Existing Project

When the user wants to move an existing project into `workspaces/`:

### 1. Check for name mismatch

Before copying, compare the local folder name against the repo name(s) on its remotes:
```bash
git -C "<source>" remote -v
```
Extract the repo name from each remote URL (strip `.git` suffix, take the last path component). If any remote name differs from the local folder name, present options:

> Local folder is "Apps" but remote says "search.tcl.local". What should the workspace be named?
> 1. search.tcl.local (from origin)
> 2. Apps (keep current name)

If multiple remotes have different repo names, list all unique names as options. Use the chosen name as the target directory name under `workspaces/{Org}/`.

### 2. Copy local

**Copy local** (default) -- `cp -r <source> <target>`. This preserves gitignored files, local configs, build artifacts, `deps/`, `.claude/settings.local.json`, and untracked reference material. Preferred over cloning from remote.

**Clone from remote** -- Only if the user explicitly requests a clean clone, or if no local copy exists.

Before copying, check and report the source repo's state:
```bash
git -C "<source>" status --short
```
Inform the user of any dirty state (modified files, untracked files, uncommitted changes). This is informational -- proceed with the copy regardless, since preserving local state is the point.

### 3. Migrate session history

After copying into `workspaces/`, migrate session history so `/resume` works at the new path:
```bash
python scripts/migrate-sessions.py "<old-path>" "<new-path>"
```

If the script reports no existing sessions, that's fine -- skip silently.

## New Workspace Setup

For new workspaces (no existing project to import):
1. If a git remote URL is provided, clone it: `git clone <url> <target-path>`
2. If no remote, create the directory and `git init` inside it
3. Add `deps/` to the project's `.gitignore` (for pinned external reference material)

## Steps

1. **Detect workspace type** -- Check if the target path has existing files.
   - **Empty directory**: New project. Ask the user what they're building.
   - **Existing project**: Scan for language files, package manifests, build configs to auto-detect the stack. Confirm findings with the user.

2. **Git init** -- If not already a git repo (skip for copied/cloned repos):
   - Empty dir: `git init`
   - Existing project: `git init && git add -A && git commit -m "Initial commit"` (snapshot before changes)

3. **Gather project info** -- Use AskUserQuestion for anything not auto-detected:
   - What does this project do? (one sentence)
   - Tech stack (language, framework, build tool, test runner)
   - Commands to build/test/run
   - Work or personal project? (pre-filled if org folder was chosen)

4. **Create CLAUDE.md** -- Keep under 500 lines. Include:
   - Purpose (one paragraph)
   - Platform (Windows 11, reference shell rules)
   - Tech stack
   - Commands (build, test, run)
   - Architecture notes (if applicable)

5. **Create .claude/settings.json** -- Stack-appropriate permissions:
   - Add `"$schema": "https://json.schemastore.org/claude-code-settings.json"` for editor autocomplete
   - Always: git read/write subcommands (explicit, not `Bash(git *)`)
   - Stack-specific: build tool, test runner, linter, package manager
   - Always deny: destructive git, sensitive files
   - Use `//path` for absolute paths (not `/path` which is relative to settings file)

6. **Deploy standard rules** -- Copy from this optimizer workspace:
   - `.claude/rules/context-handoff.md`
   - `.claude/rules/windows-shell.md`

7. **Create .gitignore** -- If none exists, create one appropriate for the stack. Always include `.claude/settings.local.json`. For nested workspaces, ensure `deps/` is included.

8. **Commit** -- `git add -A && git commit -m "Claude Code workspace setup"`.

9. **Report** -- Tell the user what was created and what they should customize.

## What This Does NOT Do

- No skills, subagents, hooks, or MCP setup (use `/optimize-workspace` for that)
- No audit or findings (this is for new projects, not existing ones)
- No playbook phases beyond basic infrastructure

This is the quick-start. `/optimize-workspace` is the full treatment.
