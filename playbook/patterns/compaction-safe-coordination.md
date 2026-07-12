# Compaction-Safe Coordination

**Source:** FortrOS paradigm-comb initiative

## When

A long-running **coordinator** (main thread) that spans compactions and delegates to
background worktree subagents. It prevents two specific failures:

1. The coordinator gets pulled into a "quick fix," iterates on it until compaction, and the
   "delegate, don't execute" posture **evaporates on the other side** -- it comes back an
   executor with half-done work that didn't survive.
2. A compacting **subthread** wakes up thinking it's the coordinator and starts merging
   neighbors / spawning subthreads -- a rogue coordinator.

This is the enforcement layer on top of [Coordination Protocol](coordination-protocol.md):
that pattern defines the roles; this one makes them survive a context reset.

## How

Deterministic mechanisms first, because behavior that depends on the model "remembering" is
exactly what a compaction erases.

1. **Two-strikes tripwire (rule, not judgment).** Any edit that doesn't compile+test green
   on the FIRST try is no longer a quick fix -- stash it and delegate. The cost asymmetry
   justifies it: a misjudged quick-fix burns the *coordinator's* context, the one that's
   expensive to lose.
2. **Compaction-safety asymmetry (the load-bearing reason).** A background worktree subagent
   *survives* compaction -- it re-invokes the lead on completion. Work the lead holds in its
   own context *evaporates*. So "delegate aggressively" is the only compaction-durable
   choice, not a preference.
3. **Role-first handoff.** `capsule.toml` leads with `ROLE: coordinator` + the in-flight
   delegation list, so the first fact reconstructed after compaction is the posture.
4. **Post-compaction re-assertion hook** -- `templates/hooks/sessionstart-coordinator.py`,
   a `SessionStart` hook with matcher `"compact"`. It re-injects the posture, and is
   **fail-safe**: it asserts the coordinator role only on positive proof (no `agent_id`, no
   `agent_type`, cwd not under `.claude/worktrees/`, a `.claude/coordinator.marker` present);
   every ambiguous case gets the *executor* posture -- because a rogue coordinator is
   catastrophic while a scoped executor is harmless. `agent_id` is the documented discriminator
   (present only inside a subagent call). CLAUDE.md auto-reloads on compaction too, so a
   `Settled Decisions` "the lead is a coordinator" row reinforces the static anchor for free.
5. **Worktree-isolation backstop** -- `templates/hooks/subagent-commit-guard.py`, a
   `PreToolUse(Bash)` guard that **blocks a subagent `git commit` on the shared main
   checkout** (`agent_id` present + git toplevel not under `.claude/worktrees/`). This kills
   the exact gate-bypass that happens when a worktree auto-cleans after a no-op run and a
   resume lands the subagent on main.
6. **Merge discipline.** Merge-base-check *every* branch before merging (a held branch gets
   inherited as a sibling's base; `rebase --onto` to decouple). Do not merge a branch while a
   review of it is still in flight (when two reviews overlap, the more skeptical one was
   right). Re-dispatch *fresh* -- never resume -- a no-op/BLOCKED worktree subagent.

## Variants

- **STEP 0 for a resume kickoff:** confirm `.claude/coordinator.marker` exists + the hook is
  wired, then read the `capsule.toml` RESUME block before reconstructing the in-chat board.
- **Residual gap (by design):** a solo subthread sharing the *main* checkout (no worktree)
  reads as coordinator -- which is why worktree-isolated subthreads are the default model.
- Pairs with [Coordination Protocol](coordination-protocol.md), [Gate Pattern](gate-pattern.md)
  (the reviewer gate the commit-guard protects), and [Nested Parallel Checkout](nested-parallel-checkout.md).
