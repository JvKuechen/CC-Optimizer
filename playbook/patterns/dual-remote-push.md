# Dual Remote Push

## Summary

Configure a git repo to push to two remotes (e.g., Gitea LAN + GitHub WAN) with a single `git push` command. Uses git's multiple push URL feature on one remote.

## Remote Strategy

Every project gets a local Gitea remote. Some also get GitHub.

| Category | Gitea Remote | GitHub Remote | Dual Push? |
|----------|-------------|---------------|------------|
| Work | `gitea.example.com` (always) | No (internal only) | No |
| Personal | `git.example.com` (always) | Private repo for sync/backup | Yes |
| Personal (public) | `git.example.com` (always) | Public repo for portfolio | Yes |

**Gitea is always the primary remote** (LAN, fast, always available). GitHub is the optional WAN mirror for backup, sync, or public visibility.

**GitHub privacy rule:** Dual-push sync only targets private GitHub repos unless the repo is already public. Check repo privacy before adding as a push URL: `gh repo view user/repo --json isPrivate -q .isPrivate`

## When to Use

- Project needs both a LAN Gitea repo AND a GitHub mirror
- Any repo that needs synchronized mirrors without a dedicated sync service
- Projects where forgetting to push to one remote causes drift

## How It Works

- **Push**: Git sends to ALL push URLs configured on a remote. One command, both updated.
- **Fetch**: Git only fetches from the single fetch URL. One remote = one fetch source.
- **Secondary remote**: Keep it around for direct fetch if you need to pull from the other source.

## Setup

Gitea (`origin`) is always the primary remote. Add GitHub as a second push URL:

```bash
# Add both push URLs to the primary remote.
# IMPORTANT: The first --add --push REPLACES the implicit "use fetch URL for push",
# so you must explicitly add the original URL too.
git remote set-url --add --push origin https://git.example.com/user/repo.git
git remote set-url --add --push origin https://github.com/user/repo.git

# Add github as standalone remote for direct fetch if needed
git remote add github https://github.com/user/repo.git
```

Result:
```
origin  https://git.example.com/user/repo.git (fetch)
origin  https://git.example.com/user/repo.git (push)
origin  https://github.com/user/repo.git (push)
github  https://github.com/user/repo.git (fetch)
github  https://github.com/user/repo.git (push)
```

For Work projects (Gitea only, no dual push):
```
origin  https://gitea.example.com/ExampleOrg/repo.git (fetch)
origin  https://gitea.example.com/ExampleOrg/repo.git (push)
```

## Gitea Instances

| Instance | URL | Category | Org/User |
|----------|-----|----------|----------|
| Work | `gitea.example.com` | Work projects | `ExampleOrg` |
| Personal | `git.example.com` | Personal projects | TBD |

## Gotchas

- If one push URL fails (e.g., GitHub down), the push still succeeds for the other but git reports an error. The remotes will be out of sync until you push again when both are up.
- Branch tracking only follows one remote. `git pull` fetches from the tracked remote only.
- Pre-push hooks fire once per push URL, so hooks that push nested repos (like wiki/) will run twice. Make sure they're idempotent.
- To remove a push URL: `git remote set-url --delete --push origin https://url-to-remove`
- `git remote -v` shows the config. If you see only one push URL, the implicit default is still active.
- **Privacy check before adding GitHub push URL**: Only sync to private repos unless the project is intentionally public. Use `gh repo view` to verify.

## During Optimization

When setting up a workspace's git remotes:

1. Check `git remote -v` -- what exists?
2. Ensure Gitea remote exists (`gitea.example.com` for Work, `git.example.com` for Personal)
3. If project needs GitHub mirror: verify/create GitHub repo, check privacy
4. If dual remotes needed: add GitHub as second push URL on `origin`
5. Keep `github` as standalone remote for direct fetch
6. Document in CLAUDE.md if the dual-push setup exists, so Claude pushes to the right remote

## Real-World Examples

- **This repo** -- `github` remote pushes to both GitHub (<github-user>/<repo-name>) and Gitea (ExampleOrg/<repo-name>). Note: some repos have GitHub as primary for historical reasons; new projects should use Gitea as primary.
- **Work projects** -- Single `origin` remote pointing to `gitea.example.com`. No GitHub mirror needed.
