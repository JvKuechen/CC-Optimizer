# Main Thread Kickoff — <workspace>

Paste this to start (or resume) a main-thread coordination session. Customize the
`<placeholders>` once for the workspace, then reuse it each session. See
`~/.claude/rules/coordination.md` for the coordination protocol.

---

We are the new main thread for the <workspace> workspace. Do a wide orientation
sweep, then give me a holistic, per-area state report before we pick anything to
dig into.

Anchor the sweep on the work spine -- not random file reading:

- `git log` -- recent commits, what shipped lately
- `handoff.md` -- narrative continuity + task state from the last session, if one exists
- `CLAUDE.md` -- settled decisions and per-area status (shipped / partial / proposed)

Spawn Explore (or other read-only) subagents for breadth so the main context stays
clean.

For each area, report: what's shipped and live, what's partial, what's blocked, and
what it's waiting on. That report is the bounty board for this session -- a
structured READY / BLOCKED / PARALLEL-TRACK / SHIPPED tracker held in this
conversation, not a file. Rebuild it from the spine; never read it from or write it
to disk. I want the full picture first.

<ENVIRONMENT READINESS -- replace with workspace-specific checks, or delete if the
workspace has no separate dev/test environment. Example: "The dev environment was
brought up in another thread -- confirm with `<status command>`. You can reach
`<live system>` to test things you're unsure of.">

Then we choose a target together based on what unblocks the most. Surface the
candidates with tradeoffs and leave the choice open. If my read of the workstream
looks off, say so before we dig in — a wrong target caught now is cheap.

<SEQUENCING NOTE -- optional. If the workspace's areas cross-influence each other,
keep this: "The areas enhance each other, so rotating between them usually beats
hammering one -- a change in one place often reshapes how another should be built."
Delete if the work is linear.>
