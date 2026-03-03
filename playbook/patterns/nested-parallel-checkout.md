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

## Variant: Tracked Content with CI Sync

An alternative where the parent repo tracks the nested content and CI workflows push it to the wiki repo on push to main. No local subrepo or hooks needed -- just the content directory and a workflow file. This provides:

- Single source of truth (parent repo)
- Normal search/grep includes nested content
- Wiki remote kept in sync automatically via CI
- One-way flow: parent -> wiki repo (no editing via wiki tab)
- No per-machine setup (no subrepo clone, no hooks)

Trade-off: wiki tab edits are disallowed (content flows from parent only). Requires CI (GitHub Actions or Gitea Actions).

The workflow file is generic -- uses `github.server_url` and `github.repository` context variables, so one template works across all repos. Add a `concurrency` group with `cancel-in-progress: true` to prevent rapid pushes from queuing.

Used by CC-Optimizer and all WS/ workspaces with wikis.

### Migration: Gitignored to CI-Synced

To convert an existing gitignored nested checkout to tracked content with CI sync:

1. Commit any uncommitted changes in the nested repo first
2. Change `.gitignore`: `wiki/` -> `wiki/.git/` (or remove the entry entirely)
3. **Gitlink workaround**: `git add wiki/` will detect `wiki/.git` and add a gitlink (submodule pointer) instead of actual files. Fix by temporarily hiding `.git`:
   ```bash
   mv wiki/.git wiki/.git_temp
   git add wiki/
   mv wiki/.git_temp wiki/.git
   git rm --cached -r wiki/.git_temp/   # clean up any accidentally staged .git internals
   ```
   This only needs to happen once (the initial add). After wiki files are in the index as regular blobs, subsequent `git add wiki/file.md` works normally.
4. Add `.gitea/workflows/wiki-sync.yml` (copy from CC-Optimizer -- works as-is for any repo)
5. Ensure wiki repo exists on the platform (create first page via UI if needed)
6. Ensure `WIKI_TOKEN` and `INTERNAL_CA_PEM` secrets are available (org-level on Gitea)
7. Delete `wiki/.git/` locally (no longer needed)
8. Remove any wiki-related hooks (post-commit, pre-push wiki section)
9. Commit, push, verify CI workflow syncs to wiki repo

See `scripts/rollout-wiki-sync.py` in CC-Optimizer for batch migration across workspaces.

## Real-World Examples

- **CC-Optimizer/wiki/** -- CI-synced variant. Wiki markdown is committed to the main repo; GitHub Actions and Gitea Actions workflows push content to wiki repos on push to main. No local subrepo.
- **All WS/ workspaces with wikis** -- Same CI-synced pattern. Rolled out via `scripts/rollout-wiki-sync.py`. Generic workflow file, org-level secrets.
- **project-alpha/wiki/** -- Gitea wiki for IT infrastructure docs. Parent is IaC (etc/, opt/, deploy/), wiki is user-facing documentation. CI-synced on push to main.
