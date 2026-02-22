---
name: init-workspace
description: Bootstrap a new Claude Code workspace with standard infrastructure
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
argument-hint: "[path-to-workspace]"
---

Bootstrap a new Claude Code workspace at `$ARGUMENTS`.

## Steps

1. **Detect workspace type** — Check if the target path has existing files.
   - **Empty directory**: New project. Ask the user what they're building.
   - **Existing project**: Scan for language files, package manifests, build configs to auto-detect the stack. Confirm findings with the user.

2. **Git init** — If not already a git repo:
   - Empty dir: `git init`
   - Existing project: `git init && git add -A && git commit -m "Initial commit"` (snapshot before changes)

3. **Gather project info** — Use AskUserQuestion for anything not auto-detected:
   - What does this project do? (one sentence)
   - Tech stack (language, framework, build tool, test runner)
   - Commands to build/test/run
   - Work or personal project?

4. **Create CLAUDE.md** — Use `templates/CLAUDE-TEMPLATE.md` as a starting point. Fill in from auto-detection + user answers. Keep under 500 lines. Include:
   - Purpose (one paragraph)
   - Platform (Windows 11, reference shell rules)
   - Tech stack
   - Commands (build, test, run)
   - Architecture notes (if applicable)

5. **Create .claude/settings.json** — Stack-appropriate permissions:
   - Add `"$schema": "https://json.schemastore.org/claude-code-settings.json"` for editor autocomplete
   - Always: git read/write subcommands (explicit, not `Bash(git *)`)
   - Stack-specific: build tool, test runner, linter, package manager
   - Always deny: destructive git, sensitive files
   - Use `//path` for absolute paths (not `/path` which is relative to settings file)

6. **Deploy standard rules** — Copy from this optimizer workspace:
   - `.claude/rules/context-handoff.md`
   - `.claude/rules/windows-shell.md`

7. **Create .gitignore** — If none exists, create one appropriate for the stack. Always include `.claude/settings.local.json`.

8. **Commit** — `git add -A && git commit -m "Claude Code workspace setup"`.

9. **Report** — Tell the user what was created and what they should customize.

## What This Does NOT Do

- No skills, subagents, hooks, or MCP setup (use `/optimize-workspace` for that)
- No audit or findings (this is for new projects, not existing ones)
- No playbook phases beyond basic infrastructure

This is the quick-start. `/optimize-workspace` is the full treatment.
