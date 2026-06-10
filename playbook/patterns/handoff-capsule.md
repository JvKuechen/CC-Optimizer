# Handoff Capsule

**Source:** FortrOS workflow-token review (the 91.6M cache-read coordinator transcript)

## When

Any workspace running the coordination protocol with a gitignored `handoff.md` and a
long-lived coordinator that restarts, resumes, or compacts. The cost it kills: every
session start re-reading (or worse, re-deriving via git log + file sweeps) the full
handoff narrative just to learn the current state.

## How

One `handoff.md` stays the sole state file. A marker-delimited **capsule** near its top
holds the live state; a `SessionStart` hook (`templates/hooks/handoff-capsule.py`)
injects ONLY the capsule into context on every session start.

```md
<!-- CLAUDE_HANDOFF_CAPSULE_BEGIN -->
## ROLE
## CURRENT GOAL
## CURRENT STATE
## ACTIVE WAVE
## HOLDS AND GATES
## NEXT SAFE ACTION
## OPEN FOLLOW-ONS
<!-- CLAUDE_HANDOFF_CAPSULE_END -->
```

Operating rules (the hook's injected header restates them every session, so they
self-reinforce):

- Update the capsule **in place** as truth changes.
- Append wave closeouts **below** the capsule -- history accumulates under it, never in it.
- One file. Rejected: a structured sidecar (`handoff.state.toml`) -- with two state
  files one always goes stale, because fast wave work updates only the one in hand.
- Rejected: line-range addressing into markdown -- line numbers shift under normal
  edits; markers are stable.
- Rejected: an MCP server for handoff state -- the problem is freshness + extraction,
  not query semantics; a process + schema + extra tool turns costs more than it saves.

## Settled design verdicts

1. **Inject on every SessionStart source** (startup, resume, compact, clear). The
   capsule is ~1-2k tokens; one avoided rediscovery pass pays for weeks of injections.
2. **Coordinator-only.** The hook skips silently for subagents (`agent_id`/`agent_type`)
   and worktree cwds -- a scoped executor must not inherit the coordinator's
   NEXT SAFE ACTION. Same fail-safe posture as `sessionstart-coordinator.py`.
3. **Quiet degradation.** Missing markers fall back to a ROLE/RESUME heading heuristic
   plus a one-line self-heal nudge to add markers on the next handoff update.
4. **Marker-based extraction only.** The heading set is convention; a validator (if
   drift ever shows up) surfaces warnings at startup -- never a commit gate, because
   `handoff.md` is gitignored and commit hooks cannot see it.

## Variants

- Pairs with [Compaction-Safe Coordination](compaction-safe-coordination.md): the role
  re-assertion hook handles posture, this one handles state; post-compact the
  coordinator trusts the injected capsule and opens `handoff.md` only for history.
- Distinct from [Current State Capsule](current-state-capsule.md), which is a tracked
  CLAUDE.md section for *project* state visible to every contributor; this capsule is
  per-workstation *thread* state in the gitignored handoff.
