# Coordination Protocol

When work spans multiple sessions, multiple parallel threads, or coordination across workspaces, use this protocol. For solo-thread linear work, skip — the overhead doesn't pay off.

## Vocabulary

- **Main thread**: The coordinator. Holds the bounty board, spawns subthreads, integrates close-out reports. Long-lived across sessions.
- **Subthread**: A focused session spawned off main for a bounded task. Receives a self-contained brief, executes, returns a close-out report.
- **Bounty board**: A structured task tracker (`BOUNTY.md` at workspace root). The main thread maintains it; subthread briefs reference it.
- **Close-out report**: The structured return from a subthread — task IDs shipped (with commit hashes), test deltas, open questions, surprises, recommended next picks.

## Main thread role

You are the coordinator, not the executor.

1. **Maintain shared state** — the bounty board, handoff file, settled-decisions list.
2. **Spawn subthreads with self-contained briefs** — the subthread picks up cold from the brief alone. LAY OF THE LAND (read these files), STAGING DISCIPLINE, forewarned gotchas, expected close-out shape.
3. **Integrate close-out reports** — fold what the subthread returned back into the bounty board, save surprises as memory candidates, update sequencing.
4. **Sweep loose work** — subthreads commit only what their brief specifies. Anything else (lockfile syncs, peripheral edits, main-thread chatter that produced files) is yours to commit in logical splits after they close.

## Subthread role

You are scope-disciplined.

1. **Read the brief and orient first** — the LAY OF THE LAND names files and sections to read before deciding scope. Don't skip it.
2. **Stay in scope** — fix what the brief asks; surface other findings in the close-out report rather than fixing inline.
3. **Stage only what your task needs** — at commit time, `git status`, then `git add <specific paths>`. Never `git add -A` or `git add .`.
4. **Close with a structured report** — see "Close-out report shape" below.
5. **Ask questions when stuck** — if brief, bounty board, CLAUDE.md, and existing code don't resolve a decision, surface it to the main thread rather than guessing.

## Bounty board

When to maintain one:
- Work spans 3+ parallel threads or 3+ focus areas.
- Multiple sessions on the same workstream over weeks/months.
- Coordination across multiple workspaces (e.g., an optimizer tracking work across several targets).

When to skip: solo dev, single-session work, linear task lists.

Sections: READY / READY-after-dependency / BLOCKED / PARALLEL-TRACK / SHIPPED. Each row has ID, subject, shape (small/medium/large, in-place/worktree), and where applicable a "blocked by" column. Cumulative shipped count at the top.

See `BOUNTY.md` (planted in workspaces that use the protocol).

## Staging discipline

IMPORTANT: At commit time only.

1. `git status` — see all dirty paths.
2. Add ONLY the paths your commit needs, by filename or explicit directory.
3. Never `git add -A`, `git add .`, or `git add --all`.

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

Exception: active scoping notes in `notes/`, `findings/`, or `BOUNTY.md` itself can carry IDs while work is in flight; they retire with the cleanup pass that closes the initiative.

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
