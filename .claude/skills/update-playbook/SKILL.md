---
name: update-playbook
description: Review doc changes since last playbook update and refresh the optimization playbook
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

Update the optimization playbook based on documentation changes.

## Steps

1. **Check what changed** — Read `playbook/optimization-checklist.md` header for the "Last updated from docs" date. Compare against `docs/manifest.json` lastSync timestamp. If sync is newer, proceed.

2. **Identify changed pages** — Compare manifest `lastmod` dates against the playbook's baseline. Focus on pages most relevant to optimization:
   - best-practices.md, memory.md, settings.md, features-overview.md
   - skills.md, hooks.md, hooks-guide.md, sub-agents.md, agent-teams.md
   - plugins.md, plugins-reference.md, permissions.md, authentication.md
   - common-workflows.md, checkpointing.md, fast-mode.md, keybindings.md

3. **Read the changed pages** — For each page with a newer lastmod, read it and identify:
   - New features or configuration options
   - Changed syntax or deprecated patterns
   - New recommendations or anti-patterns

4. **Update the playbook** — Edit `playbook/optimization-checklist.md` to reflect changes:
   - Add new checklist items for new features
   - Update syntax examples if changed
   - Remove deprecated patterns
   - Update the "Last updated" date

5. **Update related files** — If changes affect:
   - Rules: update `.claude/rules/` files
   - Templates: update `templates/user-settings.json`
   - Skills: update skill SKILL.md files
   - Agents: update agent definitions

6. **Report** — Summarize what changed in the docs and what was updated in the playbook.
