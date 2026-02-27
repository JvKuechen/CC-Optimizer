# Push Review Gate

## Summary

A PreToolUse hook that intercepts `git push` on public repos, replaces it with a diff review script, and requires the user to manually execute the push after reviewing. Deterministic -- zero LLM reasoning in the gate itself.

## When to Use

- Any repo with a `.public-repo` marker file
- Prevents accidental exposure of credentials, hostnames, or environment-specific content
- Works with dual-remote push setups (detects the remote from the command)

## How It Works

```
Claude runs: git push public main
  |
  v
PreToolUse hook fires (.claude/hooks/push-review.py)
  |
  +-- Not a git push command? -> allow through
  +-- No .public-repo marker? -> allow through
  +-- No unpushed commits?    -> allow through
  |
  v
Hook returns hookSpecificOutput with:
  - permissionDecision: "allow"
  - updatedInput.command: "python scripts/push-review.py [remote]"
  - additionalContext: tells Claude to present the review, not re-push
  |
  v
Bash tool runs push-review.py instead of git push
  |
  v
Claude presents the review output as markdown (syntax-colored diffs)
  |
  v
User reviews, then types: ! git push public main
```

## Key Design Decision: updatedInput vs block

The hook uses `updatedInput` (command swap) rather than `decision: "block"` because:

- **block** causes Claude Code to display the reason twice (hook notification + error), styled as an error with red coloring
- **updatedInput** runs the review script as normal Bash output (clean, no error styling)
- Claude re-presents the Bash output as markdown for full visibility with syntax-colored diffs (Bash output may be truncated/collapsed in the UI)
- The review script dynamically generates the `!` push command with the correct remote and branch

## Components

### `.claude/hooks/push-review.py` (PreToolUse hook)

Intercepts Bash tool calls matching `git push`. For public repos with unpushed commits, swaps the command to run the review script instead. Uses `hookSpecificOutput` format (not the deprecated top-level `decision`/`reason`).

Key implementation details:
- Derives repo root from `Path(__file__)` (not `git rev-parse --show-toplevel`, which breaks when cwd is inside a nested repo like `wiki/`)
- Auto-detects remote (prefers `public`, falls back to first remote)
- Checks `git rev-list --count` before swapping to avoid interfering with up-to-date pushes or first pushes
- Uses forward slashes in paths for Windows compatibility

### `scripts/push-review.py` (review generator)

Standalone script that outputs a markdown-formatted review:
- Commit list with short hashes
- `git diff --stat` summary
- Consolidated diff (net change, as if squashed) in a ` ```diff ` block
- Dynamic `! git push {remote} {branch}` command at the end

### `.claude/settings.json` (hook registration)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/push-review.py",
            "timeout": 15000
          }
        ]
      }
    ]
  }
}
```

### `CLAUDE.md` (behavioral instruction)

Tells Claude: the hook swaps the push command with the review script. Present the Bash output as markdown. Do NOT run git push again.

## hookSpecificOutput Format

The hook uses the current PreToolUse format (not deprecated top-level fields):

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": {
      "command": "cd \"/path/to/repo\" && python scripts/push-review.py public"
    },
    "additionalContext": "The git push was replaced with a diff review script..."
  }
}
```

| Field | Purpose |
|-------|---------|
| `permissionDecision: "allow"` | Lets the Bash tool execute (but with the swapped command) |
| `updatedInput.command` | Replaces the original `git push` with the review script |
| `additionalContext` | Tells Claude to present the output and not re-push |

## Gotchas

- **`!` command must be typed manually** -- Claude Code's `!` bash escape mode only activates when typed directly at the prompt. Tab-completing or pasting `! git push public main` types the literal text instead of entering bash mode. The user must manually type the `!` character.
- **Nested repo path resolution** -- `git rev-parse --show-toplevel` returns the wrong root when cwd is inside a nested repo with its own `.git` (e.g., `wiki/`). The hook uses `Path(__file__).resolve().parent.parent.parent` instead.
- **First push** -- When the remote tracking branch doesn't exist yet, `git rev-list` fails. The hook allows the push through so first pushes work normally.
- **Nothing to push** -- When local matches remote, the hook allows `git push` through so the user sees git's native "Everything up-to-date" message.
- **Timeout** -- The hook has a 15-second timeout. For repos with very large diffs, the review script may need more time. Increase `timeout` in settings.json if needed.
- **Non-public repos** -- The hook checks for `.public-repo` marker. Repos without this file are completely unaffected.

## Applying to Other Workspaces

To add push review to another public repo:

1. Copy `scripts/push-review.py` to the target workspace's `scripts/`
2. Copy `.claude/hooks/push-review.py` to the target workspace's `.claude/hooks/`
3. Add the PreToolUse hook to `.claude/settings.json` (see registration above)
4. Create a `.public-repo` marker file in the repo root
5. Add the "Public Repo Push Workflow" section to CLAUDE.md
6. Ensure the repo has a `scripts/verified-commit.sh` or equivalent commit workflow

If the target workspace uses a different remote naming convention, the hook auto-detects (prefers `public`, falls back to first remote).
