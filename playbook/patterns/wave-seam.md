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
handoff capsule (the wave's one capsule edit; the coordinator is the only writer) ->
8. **compact or start fresh when hydration is stale**.

### The per-wave happy path (spawn-seam compact)

Validated against the FortrOS wave-2 wide pass (2026-06-12): 12 legs merged in one
evening (~4.8M subagent tokens, flat-cost), but lead usage-per-message climbed
through the integration tail -- every small fix-leg turn re-read the orientation
sweep, the interview, and nine spawn briefs. The fix is a deliberate compact at the
spawn seam, the moment that content's marginal value hits zero (each worker carries
its own brief):

1. **Kickoff + interview.** Orient from capsule + git log, then interview the user
   on anything the wave's briefs leave unsettled; validate each brief premise
   against the live tree while drafting (stale anchors are the recon-decay tax).
2. **Go wide.** Spawn every leg, then make the wave's ONE capsule edit: fold the
   interview rulings in and write the active-wave leg table into `active_wave` --
   one line per leg: slug | owned scope | branch | model | status | merge-order
   note (what it must follow / what it collides with). The post-compact lead
   routes close-outs, merges in order, and spots cross-leg collisions from this
   table, not from the discarded briefs. Whole-tree mechanical sweeps (lint /
   format combs) collide with every feature leg -- they run alone in the
   integration tail after features merge, not as a parallel leg. Then hand the
   user the standing compact, with the Keep: list naming the wave's specific
   perishables (gates awaiting a user go, adjudicated verdicts, live-hardware
   status), not just the categories:

   ```
   /compact Wave spawned; legs in flight per capsule.toml ACTIVE WAVE. Keep:
   review queue state, settled rulings from the interview. Next: integration
   tail -- reviews, fixes, merges, until single git state.
   ```

   Background subagents survive the compact -- completion notifications re-invoke
   the compacted lead.
3. **Integration tail on the lean context**: reviews, fix legs, merges, until
   single git state (main only, zero worktrees, clean status). Parallel legs
   sharing a build cache can poison each other's gate runs (stale artifacts
   carrying a sibling leg's interface changes); give legs that touch shared
   interface crates a leg-private cache, or clean the shared crates' artifacts
   before gating.
4. **Test on main, decide the next wave with the user, capsule seam edit** (fold
   close-outs into `current_state`, return `active_wave` to "none" or the next
   queue). One more wave in-session is fine; after that, close and re-kickoff
   fresh.

One compact per wave, at the spawn seam. Prefer a fresh session over a
second-generation compact -- summary-of-summary drift compounds, and the kickoff +
capsule make a cold start cheap.

### Cache heartbeat (idle waits beyond the TTL)

Doc-verified 2026-06-12 (docs/en/prompt-caching.md): a cache read resets the
TTL ("each request that hits the cache resets the timer"), and on a Claude
subscription Claude Code requests the one-hour TTL automatically for the main
conversation (API-key auth defaults to five minutes; `ENABLE_PROMPT_CACHING_1H=1`
opts in). Subagents run the five-minute TTL even on a subscription, so the
heartbeat applies to the lead only.

Economics (API list prices; subscription allowance weighting is believed to be
the same 0.1x but is not officially documented): a heartbeat turn re-reads the
context at 0.1x; a cold turn after expiry rewrites it at 2x (the 1h-TTL write
rate). Break-even ~20 beats -- hourly keep-alive is cheaper than one cold start
for any wait up to ~20 hours.

Mechanism (deterministic brick, no new tooling): when entering a wait expected
to exceed ~45 minutes with no harness-tracked completion due (a human-gated
test, a ferry gap mid-wave), arm a background sleep -- Bash `sleep 3000` with
`run_in_background: true`. Its exit notification re-invokes the lead; that turn
IS the cache read that resets the one-hour timer. Respond with a one-line delta
and re-arm; cap re-arms (~8) so an abandoned session winds down instead of
beating all night. During an active wave, leg completions land more often than
hourly and reset the timer themselves -- the heartbeat covers completion-free
gaps only.

Scope check before arming: at a natural seam (wave closed, test step done),
close the session instead -- the capsule + kickoff make a cold start cheap, and
a fresh session beats a stale warm one. The heartbeat is for mid-wave waits
where the live context is still load-bearing.

### Reject routing (workers run the five-minute TTL)

A review verdict lands well past a subagent's five-minute cache TTL, so a
resumed worker re-reads its whole transcript cache-cold (~1.25x its size at the
5m write rate). Route a Reject by shape and size (validated on the FortrOS
wave-3 tail -- two rejects, both resolved in one revision round):

- Tiny defect -> the lead fixes it on the branch itself.
- Small/mid transcript (under ~200k) or a continuation-shaped reject ("right
  approach, fix within it") -> resume the worker: SendMessage to the completed
  agent id; the harness resumes it from transcript in the background. Resume
  cost ~1.25x its transcript, and it keeps the in-head state that produces
  structural (not patch-over) remediations.
- Large transcript (~300k+) with a defect-shaped reject -> fresh fix leg
  briefed from the artifacts (review verdict + close-out + branch diff). The
  branch is the asset; the transcript dies with the worker.
- Rejected: speculative keep-alive pings on workers during review. Most legs
  pass (wave 2: 1 reject in 12), so the expected warming cost exceeds the one
  saved rewrite.

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
