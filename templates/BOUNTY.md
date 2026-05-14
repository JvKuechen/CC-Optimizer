# BOUNTY.md

<one-line description of what this workspace coordinates>

HEAD = <commit hash> · Cumulative shipped: <count>

This is the cross-thread coordination board. Main thread maintains it; subthreads reference their assigned IDs in close-out reports. See `~/.claude/rules/coordination.md` for the vocabulary.

## How to use

- **Add tasks as they surface.** Pick an ID convention (`T<n>` for code, `D-<NAME>` for migration/docs, custom prefixes for parallel tracks).
- **Mark shape.** small / medium / large; in-place / worktree. Calibrates effort expectations.
- **Move items between sections** as state changes.
- **At subthread close:** mark shipped IDs, update blocked-by chains, fold surprises into CLAUDE.md or memory.
- **Thread-local IDs live HERE and in `handoff.md` only.** Don't reference them from tracked source/docs (coordination rule, "Thread-local ID hygiene").

## READY — pick from these

| ID | Subject | Shape | Notes |
|----|---------|-------|-------|
|    |         |       |       |

## READY — after dependencies clear

| ID | Subject | Shape | Blocked by |
|----|---------|-------|------------|
|    |         |       |            |

## PARALLEL-TRACK — spawn dedicated subthreads

| ID | Subject | Shape |
|----|---------|-------|
|    |         |       |

## BLOCKED — external dependency

| ID | Subject | Blocked by |
|----|---------|------------|
|    |         |            |

## SHIPPED — recent history

Most recent first. Trim older entries to `handoff.md` archived sections when this list passes ~30 rows.

| ID | Subject | Commit |
|----|---------|--------|
|    |         |        |

## Recommended sequencing

<2-3 sentence next-moves description — what to spawn next and why, what to wait on, what's optional>
