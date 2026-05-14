# Coordination Protocol Pattern

A coordination model for workspaces with multi-thread, multi-session, or cross-workspace work. Derived from real use in a large multi-month workspace (FortrOS) where the user runs a coordinator-of-threads pattern: align once with the main thread, then ferry pasteovers between main and subthreads.

## When to install

Audit signals from the target workspace:

- Multiple `handoff.md` sections from different dates / threads
- Multiple active branches in flight simultaneously
- Multiple distinct workstreams (e.g., code + docs migration + audit-trail + parallel-track feature)
- User describes "main thread" / "subthread" / "spawn a subthread" naturally
- Cross-workspace coordination — e.g., cc-optimizer tracking work across many `WS/<project>` targets

Two or more signals = strong candidate. Single signal = optional; ask the user.

## When to skip

- Solo developer, single linear workstream
- Short-lived workspaces (script collections, throwaway experiments)
- Workspaces with a clear linear task list — coordinator overhead wastes effort

## What gets planted

| File | Where | When |
|------|-------|------|
| `coordination.md` rule | `~/.claude/rules/` (global, deployed via `templates/deploy-user-settings.py`) | Once per machine |
| `BOUNTY.md` | Workspace root | When workspace has the signals above |
| `subthread-brief.md` template | Workspace root or `playbook/` | Alongside BOUNTY.md |
| Coordination section | Generated CLAUDE.md | Init / optimize when planting BOUNTY.md |

## Deployment steps

**Machine setup (once):**

    python templates/deploy-user-settings.py

This deploys the global coordination rule to `~/.claude/rules/coordination.md` alongside settings + hooks.

**Per-workspace (init or optimize):**

1. Copy `templates/BOUNTY.md` to workspace root.
2. Copy `templates/subthread-brief.md` to workspace root.
3. Append the Coordination section to CLAUDE.md:

```markdown
## Coordination

Multi-thread work in this repo uses the coordination protocol. See `~/.claude/rules/coordination.md` for vocabulary (main thread, subthread, bounty board, close-out report) and discipline.

Spawn subthreads with the brief at `subthread-brief.md`. Maintain task state in `BOUNTY.md`. Thread-local IDs (`T<n>`, `D-*`, `#<n>`) live in those two files plus `handoff.md` only — never in tracked source/docs.
```

## Outcomes observed (FortrOS, source of this pattern)

- User aligns once with main thread; main thread keeps subthreads aligned. User role becomes ferrying pasteovers between threads, reading along, and calling out anything off.
- Subthreads return tally tables with quantified outcomes (47 retired docs walked, 1 orphan caught, 0 code-fix bounties); main thread integrates back into bounty board.
- Main thread sweeps loose files in logical commit splits after subthreads close (e.g., Cargo.lock sync separate from docs alignment separate from settings tightening).
- Subthread briefs include forewarned gotchas; close-outs report what surprised them so the next brief can pre-empt the same surprise.

## Related patterns

- **Current State Capsule** — what the bounty board references for "where are we right now"
- **Blocked Task Tracking** — the BOUNTY.md skeleton is an elaboration of this pattern with explicit shape annotations
- **Gate Pattern** — coordination protocol assumes the staging discipline gate (no `git add -A`)

## Not the same as

- **TaskList (in-thread):** TaskCreate tracks single-conversation progress; bounty board tracks cross-thread state. Both are useful and complementary.
- **handoff.md (cross-conversation):** Handoff is narrative continuity for resuming a single thread; bounty board is structured task state across many threads. Pair them.
