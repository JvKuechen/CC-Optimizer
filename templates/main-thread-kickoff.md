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
- `capsule.toml` -- the live-state capsule (role, current state, holds, next action), auto-injected at session start; edit fields in place as truth changes
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
returned report -- and run the adversarial-reviewer against the diff. Accept/Conditional
-> mergeable (Conditional files follow-ups); Reject -> re-spawn with the report. ff-merge
the reviewed branch, then `git worktree remove --force <path>` + `git branch -d
worktree-<slug>` (a worktree whose subagent made no commit auto-cleans). Full builds /
E2E / image bakes run on your main checkout, never in a worktree.

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
