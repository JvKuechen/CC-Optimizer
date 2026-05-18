# Coordination Protocol

When work spans multiple sessions, multiple parallel threads, or coordination across workspaces, use this protocol. For solo-thread linear work, skip — the overhead doesn't pay off.

## Vocabulary

- **Main thread**: The coordinator. Holds the bounty board, spawns subthreads, integrates close-out reports. Long-lived across sessions.
- **Subthread**: A focused session spawned off main for a bounded task. Receives a self-contained brief, executes, returns a close-out report.
- **Bounty board**: A structured task tracker the main thread holds in conversation context — not a file. Rebuilt from the work spine each session; embedded into subthread briefs when spawning.
- **Close-out report**: The structured return from a subthread — task IDs shipped (with commit hashes), test deltas, open questions, surprises, recommended next picks.

## Main thread role

You are the coordinator, not the executor.

1. **Maintain shared state** — the in-chat bounty board, the `handoff.md` file, the settled-decisions list.
2. **Spawn subthreads with self-contained briefs** — the subthread picks up cold from the brief alone. LAY OF THE LAND (read these files), STAGING DISCIPLINE, forewarned gotchas, expected close-out shape.
3. **Integrate close-out reports** — fold what the subthread returned back into the bounty board, save surprises as memory candidates, update sequencing.
4. **Sweep loose work** — subthreads commit only what their brief specifies. Anything else (lockfile syncs, peripheral edits, main-thread chatter that produced files) is yours to commit in logical splits after they close.

To start or resume a main-thread session, paste the workspace's `main-thread-kickoff.md` — a reusable orientation prompt anchored on the work spine (git log, `handoff.md`, settled decisions), from which the main thread reconstructs the bounty board in-chat.

## Subthread role

You are scope-disciplined.

1. **Read the brief and orient first** — the LAY OF THE LAND names files and sections to read before deciding scope. Don't skip it.
2. **Stay in scope** — fix what the brief asks; surface other findings in the close-out report rather than fixing inline.
3. **Stage only what your task needs** — at commit time, `git status`, then `git add <specific paths>`. Rejected: `git add -A` or `git add .`.
4. **Close with a structured report** — see "Close-out report shape" below.
5. **Ask questions when stuck** — if brief, bounty board, CLAUDE.md, and existing code don't resolve a decision, surface it to the main thread rather than guessing.

## Bounty board

The bounty board is an **in-chat artifact, not a tracked file**. It's a structured task tracker the main thread holds in conversation context — sections READY / READY-after-dependency / BLOCKED / PARALLEL-TRACK / SHIPPED, each row carrying ID, subject, and shape (small/medium/large, in-place/worktree).

A board only matters to the thread organizing it; once that thread closes, a persisted board is just stale drift. So it is never written to a file:

- The main thread **reconstructs** the board at session start from the work spine — `git log`, `handoff.md`, and the `CLAUDE.md` settled-decisions / status.
- When spawning a new subthread, the main thread **rewrites the whole board fresh** with current state and embeds it in the subthread brief.
- When a subthread returns and still has context runway for related work, the main thread just hands it the next task — no rewrite, it already has the lay of the land.

`handoff.md` (gitignored, per-workstation) is the only persistent local tracker. It carries durable narrative continuity; the board is live working state rebuilt from it. Persist nothing else.

When to run a board at all: work spans 3+ parallel threads or focus areas, or multiple sessions on one workstream over weeks. Skip for solo / single-session / linear work.

## Staging discipline

IMPORTANT: At commit time only.

1. `git status` — see all dirty paths.
2. Add ONLY the paths your commit needs, by filename or explicit directory.
3. Rejected: `git add -A`, `git add .`, or `git add --all`.

Why it matters:
- Subthreads commit only their work — anything else is the main thread's to sweep.
- `-A` accidentally stages between-workstation work the user is ferrying manually.
- `-A` accidentally stages credentials in untracked `.env` files.

## Thread-local ID hygiene

Task IDs that exist only in chat or scratchpads (`T\d+`, `D-*`, `#\d+` referring to in-thread numbering) don't survive thread close-out. They stop being meaningful once the thread closes.

YOU MUST NOT put these IDs in tracked content (source, docs, README, CLAUDE.md, rules files). Use instead:
- **Commit hash** — persistent, greppable.
- **Descriptive name** — "the rustdoc lint strictness flip" beats "D-LINK-STRICT".
- **Settled-decisions row reference** — for architectural decisions that live in CLAUDE.md.

Exception: the in-chat bounty board and `handoff.md` aren't tracked content — IDs live there freely. Active scoping notes in `notes/` or `findings/` may carry IDs while work is in flight; they retire with the cleanup pass that closes the initiative.

## Close-out report shape

When a subthread finishes, return a structured report.

1. **Task IDs shipped** — with commit hashes.
2. **Test coverage delta** — what new tests landed, per area.
3. **Open questions** — for follow-on subthreads.
4. **Surprises** — non-obvious findings worth carrying forward as memory candidates or settled-decisions rows.
5. **Recommended next picks** — what should follow, and why.

For verification/audit work, use a tally table:

```
| Disposition           | Count | Notes                  |
|-----------------------|-------|------------------------|
| complete-as-claimed   | 45    | confirmed at home      |
| fixed-now             | 1     | orphan caught + lifted |
| dropped-with-rationale| 1     | deferred to Phase 5+   |
```

## Natural-seam closure

Close a subthread when **work shape changes**, not when time runs out. Auditing -> new code = new subthread. Same-shape work batches well; shape-different work spawns fresh.

Calibration signals: tired-point in the conversation, context approaching 85%, work-type shift, user redirecting scope.
