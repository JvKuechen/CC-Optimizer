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
3. **Stage what your task produced** -- in an isolated per-task worktree, `git status` then `git add -A` is fine (the checkout holds only your work); on a shared main checkout, `git status` then `git add <specific paths>`. Rejected: `git add -A` on a shared main tree.
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

IMPORTANT: At commit time only. The rule depends on whether you are in an isolated worktree or a shared main checkout.

**Isolated per-task worktree** (a `claude --worktree` session, an `isolation: worktree` subagent, or an agent-team teammate that has called `EnterWorktree` -- see Worktree workflow below): the checkout holds only your task's work. `git status` to confirm the dirty set is all yours, then `git add -A` is fine.

**Shared main checkout** (solo-mode subthreads sharing one tree, or the lead's own checkout):

1. `git status` -- see all dirty paths.
2. Add ONLY the paths your commit needs, by filename or explicit directory.
3. Rejected: `git add -A`, `git add .`, or `git add --all` on a shared main tree.

Why the shared-tree rule is strict (hazards that vanish in an isolated worktree):
- A parallel thread's unstaged edits get swept in.
- Between-workstation work the user is ferrying manually gets staged.
- Credentials in untracked `.env` files get staged.

## Worktree workflow (parallel mode)

The default fan-out model is background Agent-tool subagents the lead spawns with `isolation: "worktree"` (+ `run_in_background: true`). Each gets its own checkout at `.claude/worktrees/<slug>` on branch `worktree-<slug>` from local `HEAD`, runs without moving the lead's checkout, and fires a completion notification that re-invokes the lead (survives compaction). No tmux. Two verified constraints shape the briefs:

- **Isolation is set at spawn, not self-served.** A subagent cannot create its own worktree (the harness blocks `EnterWorktree` from a subagent: "spawn an Agent with `cwd` set to it"). So the lead passes `isolation: "worktree"` on every edit-task spawn, and the brief has the subagent CONFIRM it (`git rev-parse --show-toplevel` + `git branch --show-current`): isolated = toplevel under `.claude/worktrees/` and branch `worktree-<slug>`. If it is on `main` instead, the subagent returns `BLOCKED: spawned without worktree isolation` and the lead re-spawns it with isolation set. Read-only / research subagents need no worktree.
- **Subagents cannot ask the user.** `AskUserQuestion` is unavailable to a subagent, and a background one auto-denies any prompting call and continues. So brief a subagent to return `BLOCKED: <decision>, options A/B/C, recommendation` when a decision is genuinely open, rather than guess. The lead routes it -- answering from context, or escalating to the user with its own `AskUserQuestion` (which pauses an active `/goal` loop, since it blocks mid-turn before the goal evaluator fires at turn end).

Division of labor:

- **In the worktree** (subagent, or the coordinator on a bounded task): write code, run dev + unit tests for the stack. A worktree is a fresh checkout, so gitignored files it needs (env files, local config, `handoff.md`) are copied in via a committed `.worktreeinclude` at the project root (gitignore-syntax; list only what a task legitimately needs, never signing keys or seed secrets).
- **On the lead's main checkout** (after the branch is consolidated): full builds, end-to-end runs, image bakes. These depend on shared environment state that lives on the main checkout, not in a fresh worktree. Rejected: a full build or image bake inside a worktree -- it builds against environment the worktree does not have.
- **Close-out + consolidate**: the lead reads the close-out from artifacts -- `git diff main...worktree-<slug>` + the subagent's returned report. Adversarial-review the diff (the project's reviewer subagent), ff-merge the reviewed branch into main, then run the build / E2E there. Remove the worktree after merging (`git worktree remove --force <path>` + `git branch -d worktree-<slug>`); a worktree whose subagent made no commit auto-cleans.

**Optional -- agent-team mode** (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`): the multi-teammate team UI is a separate model most workflows do not need. Teammates do NOT auto-isolate -- they start in the lead's shared checkout, so run the lead in tmux mode (`teammateMode: "tmux"`) so a teammate's `EnterWorktree` isolates only that teammate (in-process mode drags the lead), drive `EnterWorktree` from the brief, and read close-outs via `SendMessage` (a teammate's plain final message does not reach the lead). A `TeammateIdle` hook (`templates/hooks/teammate-digest.py`) can auto-capture close-outs; `TeamDelete` leaves teammate worktrees on disk. Prefer background subagents above unless you specifically need the team UI.

### Worktree base ref

New worktrees must branch from local `HEAD`, not a remote ref. Set `worktree.baseRef: "head"` -- required when the git remote is not named `origin` (the default resolution targets `origin/<default-branch>`, which a non-`origin` remote lacks, so worktree creation branches from the wrong ref or fails). Ship this in **tracked `settings.json`**, not `settings.local.json`, so every clone and workstation gets correct worktree creation.

## Thread-local ID hygiene

Task IDs that exist only in chat or scratchpads (`T\d+`, `D-*`, `#\d+` referring to in-thread numbering) don't survive thread close-out. They stop being meaningful once the thread closes.

YOU MUST NOT put these IDs in tracked content (source, docs, README, CLAUDE.md, rules files). Use instead:
- **Commit hash** — persistent, greppable.
- **Descriptive name** — "the rustdoc lint strictness flip" beats "D-LINK-STRICT".
- **Settled-decisions row reference** — for architectural decisions that live in CLAUDE.md.

Exception: the in-chat bounty board and `handoff.md` aren't tracked content — IDs live there freely. Active scoping notes in `notes/` or `findings/` may carry IDs while work is in flight; they retire with the cleanup pass that closes the initiative.

## Integration board (durable readiness)

Worker readiness must survive compaction and a dead inbox, so it lives in durable, git-truth artifacts — never in the lead's memory. (A long-lived lead can silently lose its inbox consumer on compaction/resume; relying on remembered messages is what orphans finished work.)

- **Capture** — a `TeammateIdle` hook (`teammate-digest.py`) writes each close-out to `.claude/team-digest/<name>.md` the instant a teammate goes idle, including a greppable `state=` token. Deterministic; fires whether or not `SendMessage` lands. This is what kills "finished but unread."
- **Read** — `team/worktrees-status.sh` is the lead's bird's-eye: per worktree branch, declared STATE (READY-FOR-MERGE / WAITING-FEEDBACK / BLOCKED / WORKING), commits ahead/behind, and merged? from git ancestry. Read on demand; keep it out of context until needed.
- **Merge** — lead-timed and git-truth, never on memory. `team/safe-merge.sh <branch>` holds while a build/E2E lock (`.claude/integration.lock`) is present, fast-forwards, and CONFIRMS the commit is in HEAD before returning — so testing main without the fix is impossible. No auto-gate: review stays delegated/verdict-only, merge timing is the lead's.
- **Dedupe** — before spawning a worker, check the board's declared scopes for overlap, so two workers can't ship the same fix.

The in-chat bounty board is the volatile working view; this board is the durable spine it is hydrated from.

## Close-out report shape

When a subthread finishes, return a structured report. Open with an explicit state line for the board (`STATE: READY-FOR-MERGE | WAITING-FEEDBACK | BLOCKED`) plus your branch and owned scope, then:

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
