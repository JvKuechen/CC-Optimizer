# BOUNTY.md — CC-Optimizer

Coordination board for work across the optimizer and its nested workspaces under `WS/`.

HEAD = (pre-coordination-rollout) · See git log for current cumulative shipped count

This board tracks main-thread work in CC-Optimizer plus cross-cutting initiatives that touch multiple `WS/<project>` targets. Per-workspace bounty boards (if planted) live inside their respective `WS/<project>/BOUNTY.md`. See `~/.claude/rules/coordination.md` for the protocol.

## How to use here

- Add tasks for cross-cutting work (pattern additions, rule rollouts, workspace audits).
- Per-workspace targeted work goes in `WS/<project>/handoff.md` and (if installed) `WS/<project>/BOUNTY.md` — not here.
- `playbook/roadmap.md` is the long-horizon arc; this board is the next-3-moves view.

## READY — pick from these

| ID | Subject | Shape | Notes |
|----|---------|-------|-------|
| (none open) | | | |

## PARALLEL-TRACK — spawn dedicated subthreads

| ID | Subject | Shape |
|----|---------|-------|
| | | |

## BLOCKED

| ID | Subject | Blocked by |
|----|---------|------------|
| | | |

## SHIPPED — recent

Most recent first. Trim older entries to `handoff.md` archive sections when this list passes ~30 rows.

| ID | Subject | Commit |
|----|---------|--------|
| coord-rollout | Coordination protocol scaffolding (global rule, BOUNTY/brief templates, pattern entry, init/optimize skill updates, sync-docs skill -> script migration) | (commit pending) |

## Recommended sequencing

After this commit lands:

1. **Field-test the pattern** — next time `/optimize-workspace` runs against a high-coordination target (e.g., a `WS/<project>` with multiple handoff sections or branches), watch how the detect-and-suggest path lands. Adjust signals in the skill if it over- or under-fires.
2. **Populate READY** — audit `playbook/my-roadmap.md` (gitignored) for concrete next moves and fold them in here.
3. **Consider rule consolidation** — the existing `~/.claude/rules/*.md` files (context-handoff, parallel-work, windows-shell, optimization-principles) currently live outside `templates/`. Moving them into `templates/rules/` would make `deploy-user-settings.py` the canonical redeploy path on fresh machines. Optional; the new coordination rule already follows that pattern.
