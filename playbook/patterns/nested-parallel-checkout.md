# Nested Parallel Checkout

## Summary

A git repository inside another git repository, gitignored by the parent, with its own `.git` directory and remote. NOT a submodule -- it's a parallel, independent checkout that happens to live inside the parent's directory tree.

## When to Use

- Gitea wiki repos (wiki tab requires a separate repo at `<repo>.wiki.git`)
- Documentation that lives alongside code but has a different deploy/commit lifecycle
- Content that multiple projects reference but only one project hosts
- Separating "infrastructure as code" from "documentation" in the same workspace

## Structure

```
parent-repo/
  .gitignore          # Contains: wiki/
  wiki/               # Separate git repo, gitignored by parent
    .git/             # Independent .git directory
    Home.md           # Wiki content
```

## Implementation

1. Create the nested directory (or `git clone` the target repo into it)
2. `git init` inside it if not cloned
3. Add the directory name to parent's `.gitignore`
4. Set the remote: `git -C wiki remote add origin <url>`
5. Optionally add a `.claude/rules/` rule scoped to the nested path
6. In CLAUDE.md, document the dual-repo structure so Claude doesn't confuse them

## Gotchas

- `git status` in parent will NOT show nested repo changes (it's gitignored)
- `git add -A` in parent will NOT capture nested repo content
- Claude Code may not realize the nested directory is a separate repo unless told in CLAUDE.md
- On Windows, avoid symlinks -- just use a real nested directory
- If using `--add-dir`, the nested repo gets its own context but shares permissions
- Both repos need separate push/pull workflows (consider a pre-push hook on the parent to auto-sync the nested repo)

## Real-World Examples

- **project-alpha/wiki/** -- Gitea wiki for IT infrastructure docs. Parent is IaC (etc/, opt/, deploy/), wiki is user-facing documentation. Independent commit history, auto-synced via parent's pre-push hook.
- **project-beta/wiki/** -- Gitea wiki for a knowledge base app. Same pattern: app code in parent, onboarding docs in nested wiki.
