# Wave-Seam Session Policy

**Source:** FortrOS uplift-wave transcript analysis (2026-06-10). One coordinator
session carried intake, two waves, transcript mining, crash recovery, a review hold,
and branch triage: 8 user prompts, 23 subagent launches, ~500k output tokens -- and
**91.6M cache-read tokens**, with cache-read per end-turn climbing 108k -> 395k. The
parallel work was cheap; the transcript's longevity was the cost.

## When

Multi-wave coordinator workstreams (the coordination protocol's main thread). The
failure mode: the coordinator transcript keeps accumulating wave planning, subagent
notifications, and recap turns, so every subsequent turn re-reads an ever-larger
context. On Fable 5 this is the *only* brake left -- the 1M context window means
forced compaction no longer interrupts a bloating coordinator.

## How

The seam loop, one wave per cycle:

1. Hydrate (capsule injection / kickoff) -> 2. agree the wave -> 3. dispatch worktree
subagents -> 4. collect close-outs -> 5. review -> 6. fold + test -> 7. update the
handoff capsule -> 8. **compact or start fresh when hydration is stale**.

Session discipline at each seam:

- **End or compact once the wave is in flight.** After the board is set and workers
  are running, waiting inside the transcript is pure budget drain -- completion
  notifications re-invoke a compacted lead just as well.
- **Fresh session before reviewer orchestration / hold-state decisions.** Review is
  the cleanest seam: it starts from the diff + close-outs, not from 300k+ of
  planning history.
- **Notification responses are state deltas, not recaps.** Default shape: branch,
  commit, verification status, blocker-or-merge-ready, next action. Nothing else
  unless something changed materially.
- **Summary budget: one synthesis per seam.** One after intake, one after a wave
  returns, one after verification. Everything between is a terse delta.
- **Status-watching lives outside the coordinator.** Build checkpoints and log
  monitors go to the Monitor tool or a separate cheap session, never as idle turns
  in the transcript that holds the architectural reasoning.
- Close a subthread when **work shape changes**, not when time runs out (the
  coordination protocol's natural-seam rule, applied to the coordinator itself).

## Fable 5 specifics

- **Effort, not thinking toggles.** Thinking cannot be disabled on Fable 5; the
  effort level is the lever (default `high`). Keep `high` for coordinator judgment;
  `/effort medium` fits ferry/status sessions that just route state.
- **Route cheap work via subagents or fresh sessions, never `/model` mid-session** --
  a mid-session model switch re-reads the full history uncached.
- **Slim the briefs.** Fable 5 verifies its own work and plans its own path: state
  the outcome and the boundary, drop test/verify reminders and step-by-step
  prescriptions. (Also see the positive-instruction-framing rule: no time/context
  budget framing in briefs.)
- **Cross-vendor review fits here.** A different-vendor reviewer (e.g. the official
  OpenAI codex plugin's read-only `/codex:adversarial-review`) moves review tokens
  off the coordinator's subscription AND brings a different failure prior. Flow:
  Claude implements -> Codex reviews the branch -> Claude folds + tests. Keep the
  reviewer read-only; the implementing side keeps the single-writer test/merge leg.

## Variants

- Pairs with [Handoff Capsule](handoff-capsule.md) (makes step 1 cheap enough to do
  often) and [Compaction-Safe Coordination](compaction-safe-coordination.md) (makes
  step 8 safe -- posture and in-flight delegations survive the reset).
- For measurement: cache-read-per-turn growth is the tell. If end-turn cache reads
  double across a session, a seam was missed.
