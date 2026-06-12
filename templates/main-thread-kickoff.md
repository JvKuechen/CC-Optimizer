# Main Thread Kickoff — <workspace>

Paste this to start (or resume) a main-thread coordination session. Customize the
`<placeholders>` once for the workspace, then reuse it each session. See
`~/.claude/rules/coordination.md` for the coordination protocol.

---

We are the new main thread for the <workspace> workspace. Do a wide orientation
sweep, then give me a holistic, per-area state report before we pick anything to
dig into.

Anchor the sweep on the work spine -- the anchors below, read in order:

- `git log` -- recent commits, what shipped lately
- `capsule.toml` -- the live-state capsule (role, current state, holds, next action), auto-injected at session start. You are its only writer: edit its fields once per wave seam (wave close, direction change, pre-compact), folding worker close-outs in then; workers read it and report back through their close-outs
- `CLAUDE.md` -- settled decisions and per-area status (shipped / partial / proposed)

Spawn Explore (or other read-only) subagents for breadth so the main context stays
clean.

For each area, report: what's shipped and live, what's partial, what's blocked, and
what it's waiting on. That report is the bounty board for this session -- a
structured READY / BLOCKED / PARALLEL-TRACK / SHIPPED tracker that lives
in this conversation, rebuilt from the spine each session. I want the
full picture first.

<ENVIRONMENT READINESS -- replace with workspace-specific checks, or delete if the
workspace has no separate dev/test environment. Example: "The dev environment was
brought up in another thread -- confirm with `<status command>`. You can reach
`<live system>` to test things you're unsure of.">

Then we choose a target together based on what unblocks the most. Surface the
candidates with tradeoffs and leave the choice open. If my read of the workstream
looks off, say so before we dig in — a wrong target caught now is cheap.

## Coordination -- foreground lead + background worktree subagents

You run foreground on `main` and edit it directly (foreground sessions are exempt from
worktree isolation). Parallel work goes to BACKGROUND subagents via the Agent tool with
`isolation: "worktree"` (+ `run_in_background: true`): each gets its own checkout from
local `HEAD`, runs without moving yours, and fires a completion notification that
re-invokes you (survives compaction) -- so you do not poll. No tmux. Give each subagent a
disjoint file set. Briefs state the outcome and the boundary, not the steps; on Fable 5
omit test/verify reminders -- it verifies its own work, and reminders just pad the brief.

Two verified constraints shape the briefs:

- **Set isolation at spawn.** A subagent cannot create its own worktree (the harness
  blocks `EnterWorktree` from a subagent), so pass `isolation: "worktree"` on every
  edit-task spawn. The brief has the subagent confirm it landed in a worktree and return
  `BLOCKED: spawned without worktree isolation` if it is on `main`; re-spawn it with
  isolation set. Read-only / research subagents need no worktree.
- **Subagents cannot ask the user.** `AskUserQuestion` is unavailable to a subagent;
  brief it to return `BLOCKED: <decision>, options A/B/C` rather than guess. You route it
  -- answer from context, or escalate with your own `AskUserQuestion` (which pauses an
  active `/goal`, since it blocks mid-turn before the goal evaluator fires at turn end).

Read each close-out from artifacts -- `git diff main...worktree-<slug>` + the subagent's
returned report (its final message arrives verbatim as the tool result; the worker's job
ends at the message). Run the adversarial-reviewer (or the Codex reviewer leg,
backgrounded: `scripts/codex-review.sh --base main --repo <worktree> --tag <slug>
--closeout-text "<the returned report>"`) against the diff -- the inline close-out feeds
the claims cross-check, and the script persists it to `findings/<slug>-closeout.md` as
the durable copy. Accept/Conditional
-> mergeable (Conditional files follow-ups); Reject -> re-spawn with the report. ff-merge
the reviewed branch, then `git worktree remove --force <path>` + `git branch -d
worktree-<slug>` (a worktree whose subagent made no commit auto-cleans). Full builds /
E2E / image bakes run on your main checkout, never in a worktree.

## Wave rhythm -- interview, go wide, compact at the spawn seam

Each wave runs one seam loop:

1. **Orient + interview.** After the lay-of-the-land report, interview the user on
   anything the wave's briefs leave unsettled; validate each brief premise against
   the live tree while drafting (stale anchors are the recon-decay tax).
2. **Go wide.** Spawn every leg, then make the wave's ONE capsule edit: fold the
   interview rulings in and write the active-wave leg table into `active_wave` --
   one line per leg: slug | owned scope | branch | model | status | merge-order
   note (what it must follow / what it collides with). The post-compact you routes
   close-outs, merges in order, and spots cross-leg collisions from this table,
   not from the spawn briefs (each worker carries its own). Whole-tree mechanical
   sweeps (lint / format combs) collide with every feature leg -- they run alone
   in the integration tail after features merge, not as a parallel leg. Then hand
   the user the standing compact, with the Keep: list naming the wave's specific
   perishables (gates awaiting a user go, adjudicated verdicts, live-hardware
   status):

   ```
   /compact Wave spawned; legs in flight per capsule.toml ACTIVE WAVE. Keep:
   review queue state, settled rulings from the interview. Next: integration
   tail -- reviews, fixes, merges, until single git state.
   ```

   Background subagents survive the compact -- their completion notifications
   re-invoke you.
3. **Integration tail** on the lean context: reviews, fix legs, merges, until single
   git state (main only, zero worktrees, clean status).
4. **Test on main, decide the next wave with the user, capsule seam edit** (fold
   close-outs into `current_state`, return `active_wave` to "none" or the next
   queue). One more wave in-session is fine; after that, close and re-kickoff fresh
   -- one compact per wave, and a fresh session beats a second-generation compact.

Mid-wave waits with no completion due within the hour (a human-gated test, a
ferry gap): arm a cache heartbeat -- background Bash `sleep 3000`; its exit
notification re-invokes you, and that turn resets the subscription cache's
one-hour timer. Reply with a one-line delta and re-arm, capping at ~8 beats.
Leg completions reset the timer on their own; the heartbeat covers
completion-free gaps only. At a natural seam, close the session instead.

If you drive the session under `/goal`, state the condition transcript-demonstrable +
bounded (the evaluator only reads the conversation) and it reprompts each turn until met.
Prune completed tasks as you go so a stale completed-heavy list does not prime a premature
stop.

**Optional -- agent-team mode** (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`): a separate
multi-teammate UI most workflows do not need. It requires tmux (`teammateMode: "tmux"`)
so a teammate's `EnterWorktree` does not drag the lead, drives `EnterWorktree` from the
brief, and leans on a durable board (`templates/team/worktrees-status.sh`,
`safe-merge.sh`, the `TeammateIdle` digest, `inbox-recovery.py`) because teammate
`SendMessage` can be lost on a compaction-killed inbox. See the
`agent-teams-worktree-isolation` memory. Prefer background subagents above.

<SEQUENCING NOTE -- optional. If the workspace's areas cross-influence each other,
keep this: "The areas enhance each other, so rotating between them usually beats
hammering one -- a change in one place often reshapes how another should be built."
Delete if the work is linear.>
