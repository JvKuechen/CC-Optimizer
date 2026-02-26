# Dual Remote Push

## Summary

Configure a git repo to push to two remotes (e.g., Gitea LAN + GitHub WAN) with a single `git push` command. Uses git's multiple push URL feature on one remote.

## Remote Naming Convention

The remote name signals visibility and function:

| Scenario | Name | Rationale |
|----------|------|-----------|
| Any public remote in the push URLs | `public` | Warning label -- every `git push public` reminds you the world can see it |
| Single private remote | Host name (`gitea`, `github`, etc.) | Obvious, no ambiguity |
| Multiple private remotes (bridge pattern) | `mirrors` | Describes function (syncing between environments), makes no privacy claim, won't go stale if a remote later changes visibility |

## Remote Strategy

Every project gets a local Gitea remote. Some also get GitHub.

| Category | Gitea Remote | GitHub Remote | Dual Push? | Remote Name |
|----------|-------------|---------------|------------|-------------|
| Work only | Always | No | No | `gitea` |
| Private bridge | Always | Private repo for sync | Yes | `mirrors` |
| Public | Always | Public repo | Yes | `public` |

**Gitea is always the primary remote** (LAN, fast, always available). GitHub is the optional WAN mirror for backup, sync, or public visibility.

**GitHub privacy rule:** Dual-push sync only targets private GitHub repos unless the repo is already public. Check repo privacy before adding as a push URL: `gh repo view user/repo --json isPrivate -q .isPrivate`

## When to Use

- Project needs both a LAN Gitea repo AND a GitHub mirror
- Any repo that needs synchronized mirrors without a dedicated sync service
- Projects where forgetting to push to one remote causes drift

## How It Works

- **Push**: Git sends to ALL push URLs configured on a remote. One command, both updated.
- **Fetch**: Git only fetches from the single fetch URL. One remote = one fetch source.
- **Secondary remote**: Keep standalone named remotes around for direct fetch if you need to pull from the other source.

## Setup

### Public repo (any push URL is public)

```bash
# Rename existing remote to 'public'
git remote rename origin public
# Or if starting fresh:
git remote add public https://git.example.com/org/repo.git

# Add GitHub public as second push URL
git remote set-url --add --push public https://git.example.com/org/repo.git
git remote set-url --add --push public https://github.com/user/repo.git

# Keep github as standalone for direct fetch
git remote add github https://github.com/user/repo.git

# Track the dual-push remote
git branch --set-upstream-to=public/main main
```

Result:
```
public  https://git.example.com/org/repo.git (fetch)
public  https://git.example.com/org/repo.git (push)
public  https://github.com/user/repo.git (push)
github  https://github.com/user/repo.git (fetch)
github  https://github.com/user/repo.git (push)
```

### Private bridge (multiple private remotes)

```bash
git remote add mirrors https://git.example.com/org/repo.git
git remote set-url --add --push mirrors https://git.example.com/org/repo.git
git remote set-url --add --push mirrors https://github.com/user/repo-private.git

# Keep standalone remotes for direct fetch
git remote add gitea https://git.example.com/org/repo.git
git remote add github https://github.com/user/repo-private.git

git branch --set-upstream-to=mirrors/main main
```

### Work only (single Gitea, no dual push)

```
gitea  https://gitea.example.com/org/repo.git (fetch)
gitea  https://gitea.example.com/org/repo.git (push)
```

## Gotchas

- If one push URL fails (e.g., GitHub down), the push still succeeds for the other but git reports an error. The remotes will be out of sync until you push again when both are up.
- Branch tracking only follows one remote. `git pull` fetches from the tracked remote only.
- Pre-push hooks fire once per push URL, so hooks that push nested repos (like wiki/) will run twice. Make sure they're idempotent.
- To remove a push URL: `git remote set-url --delete --push <remote> https://url-to-remove`
- `git remote -v` shows the config. If you see only one push URL, the implicit default is still active.
- **Privacy check before adding GitHub push URL**: Only sync to private repos unless the project is intentionally public. Use `gh repo view` to verify.
- When renaming remotes, update branch tracking: `git branch --set-upstream-to=<new-name>/main main`

## During Optimization

When setting up a workspace's git remotes:

1. Check `git remote -v` -- what exists?
2. Ensure Gitea remote exists
3. If project needs GitHub mirror: verify/create GitHub repo, check privacy
4. Determine naming: `public` (any public push URL), `mirrors` (all private bridge), or host name (single remote)
5. Add second push URL to the named remote
6. Keep standalone remotes for direct fetch from either source
7. Set branch tracking to the dual-push remote
8. Document in CLAUDE.md if the dual-push setup exists, so Claude pushes to the right remote
