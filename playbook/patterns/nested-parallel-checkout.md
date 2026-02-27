# Nested Parallel Checkout

## Summary

A git repository inside another git repository, gitignored by the parent, with its own `.git` directory and remote. NOT a submodule -- it's a parallel, independent checkout that happens to live inside the parent's directory tree.

## When to Use

- GitHub/Gitea wiki repos (wiki tab requires a separate repo at `<repo>.wiki.git`)
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
- **GitHub wikis require the `master` branch** -- do not rename to `main`. GitHub's wiki tab only reads from `master`. Gitea wikis also default to `master`. If your pre-push hook pushes the wiki, detect the branch dynamically rather than hardcoding `main`
- On Windows, avoid symlinks -- just use a real nested directory
- If using `--add-dir`, the nested repo gets its own context but shares permissions
- Both repos need separate push/pull workflows (consider a pre-push hook on the parent to auto-sync the nested repo)

## Variant: Tracked Content with Gitignored .git

An alternative where the parent repo tracks the nested content but gitignores only the `.git/` directory. A post-commit hook in the parent auto-commits to the nested repo when parent commits touch the nested directory. This provides:

- Single source of truth (parent repo)
- Normal search/grep includes nested content
- Wiki remote kept in sync automatically
- One-way flow: parent -> nested repo (no editing via wiki tab)

Trade-off: wiki tab edits are disallowed (content flows from parent only).

Used by CC-Optimizer itself for its GitHub wiki.

### Migration: Gitignored to Tracked

To convert an existing gitignored nested checkout to tracked content:

1. Commit any uncommitted changes in the nested repo first
2. Change `.gitignore`: `wiki/` -> `wiki/.git/`
3. **Gitlink workaround**: `git add wiki/` will detect `wiki/.git` and add a gitlink (submodule pointer) instead of actual files. Fix by temporarily hiding `.git`:
   ```bash
   mv wiki/.git wiki/.git_temp
   git add wiki/
   mv wiki/.git_temp wiki/.git
   git rm --cached -r wiki/.git_temp/   # clean up any accidentally staged .git internals
   ```
   This only needs to happen once (the initial add). After wiki files are in the index as regular blobs, subsequent `git add wiki/file.md` works normally.
4. Install the post-commit hook (see CC-Optimizer's `scripts/setup.py` for the template)
5. Commit, verify the post-commit hook creates a wiki commit
6. Delete the grep-wiki-reminder hook if you had one (no longer needed)

## Real-World Examples

- **CC-Optimizer/wiki/** -- Tracked content variant. Wiki markdown is committed to the main repo; a post-commit hook silently syncs changes into the wiki subrepo. Pre-push hook pushes the wiki when the main repo pushes.
- **project-alpha/wiki/** -- Gitea wiki for IT infrastructure docs. Parent is IaC (etc/, opt/, deploy/), wiki is user-facing documentation. Independent commit history, auto-synced via parent's pre-push hook.
- **project-beta/wiki/** -- Gitea wiki for a knowledge base app. Same pattern: app code in parent, onboarding docs in nested wiki.
