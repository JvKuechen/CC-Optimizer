# Subthread Brief — <task or initiative name>

<!-- Authoring note (delete before pasting): state the OUTCOME and the boundary, not
the steps. On Fable 5, omit test/verify reminders -- the model verifies its own work;
reminders just pad the brief. No time/context-budget framing (see
positive-instruction-framing). -->

You are a subthread of the main thread for <workspace>. The main thread maintains the bounty board and integrates close-out reports. Get the lay of the land first, then execute the assigned task.

## LAY OF THE LAND

Read these in order before deciding scope:

1. `capsule.toml` — most recent section first. Status of the broader workstream.
2. `CLAUDE.md` — settled decisions, conventions, gotchas. Note the IMPORTANT / YOU MUST lines.
3. <task-specific files: scoping doc path, target source files with their doc-comments, related tests, ADRs>

The current bounty board is embedded in the Task scope section below — the main thread rewrote it fresh for this spawn. Read source-of-truth for your task before committing to scope (the scoping doc, the existing module's doc-comments, related ADRs) — not just the one-line bounty subject.

## YOUR WORKTREE -- confirm before editing

Before any edit, confirm whether you are in an isolated worktree:

    git rev-parse --show-toplevel && git branch --show-current

You are isolated when the toplevel is under `.claude/worktrees/` and the branch is `worktree-<slug>`. Then act by task type:

- **Read-only / research task** -> proceed as-is; you need no worktree.
- **Edit task, already isolated** -> do all edits + commits here; the lead merges the branch to main at close-out.
- **Edit task, NOT isolated** (toplevel is the repo root / branch is `main`) -> do not edit. Return `BLOCKED: spawned without worktree isolation` and stop. A background subagent cannot create its own worktree (the harness blocks `EnterWorktree` from a subagent), so the lead re-spawns you with isolation set.

## STAGING DISCIPLINE

Stage at commit time only:

- Confirmed isolated (your own worktree): `git status` to confirm the dirty set is all yours, then `git add -A` is fine -- the checkout holds only your work.
- On a shared main checkout (a task the lead scoped to run on main): `git status`, then add ONLY the paths your task needs, by explicit filename or directory. Rejected: `git add -A` / `git add .` on a shared main tree -- it sweeps parallel edits or hand-ferried files.

Anything else dirty in the tree is the main thread's to sweep after you close.

## FOREWARNED GOTCHAS

<project-specific constraints that will bite on close-out if forgotten — lint strictness, link syntax, naming conventions, performance budgets, platform quirks. Examples below; replace with workspace-specific items.>

- Example: pre-commit hook blocks `git commit` on this repo; use `scripts/verified-commit.sh -m "..."` instead.
- Example: rustdoc intra-doc links to non-dep crates fail; use plain backticks for cross-workspace references.
- Example: file writes produce CRLF on Windows; the fix-line-endings hook handles it — leave file encoding to the hook.

## ASKING QUESTIONS

When the brief (the embedded board included), CLAUDE.md, or existing code leave a decision open, raise it to the main thread. The main thread will fork to resolve and resume the subthread with the answer.

If the brief's approach itself looks wrong — not merely unclear, but headed somewhere bad — say so before executing rather than complying cleanly. A flawed brief caught early is cheaper than a polished execution of it.

Look-ups (file reads, grep, re-reading sections already cited above) stay in-thread.

## COMMITS

<commit message format for this workstream>

Example shape:

    <prefix>: <task-id-or-name>: <one-line summary>

Examples:

    audit-tail: T58b: at-boot substrate derivation of org_unmask_key
    docs-migration: D-RETIRE-VERIFY: final reference sweep

## WHAT TO RETURN AT CLOSE-OUT

End with an explicit state line so the readiness board is deterministic:

    STATE: READY-FOR-MERGE | WAITING-FEEDBACK | BLOCKED

- **READY-FOR-MERGE** — reviewed-clean in your own judgment; branch holds for the lead.
- **WAITING-FEEDBACK** — a decision is open; say what you need.
- **BLOCKED** — can't proceed; say on what.

Then the report:

1. **Branch + scope** — your `worktree-<slug>` branch and the files/scope you owned (lets the lead dedupe before spawning the next worker).
2. **Task IDs shipped** — with commit hashes.
3. **Test coverage delta** — per crate/module if applicable.
4. **Open questions** — for follow-on subthreads.
5. **Surprises** — non-obvious findings worth saving as memory or settled decisions.
6. **Recommended next picks** — what should follow, and why.

Your FINAL MESSAGE is the close-out the lead reads (together with `git diff main...worktree-<slug>`); lead with the STATE line. **Hold on your branch** — the lead reviews and merges at a seam; do not merge to main yourself. (In the optional agent-team mode, also `SendMessage` it to `team-lead`, since a teammate's plain final message does not reach the lead there.)

For verification/audit work, include a tally table with explicit dispositions:

    | Disposition          | Count | Notes |
    |----------------------|-------|-------|
    | complete-as-claimed  |       |       |
    | fixed-now            |       |       |
    | dropped-with-rationale|      |       |

## Task scope

<paste the current bounty board — rewritten fresh by the main thread for this spawn — plus your task's row and any expansion>

What is the most correct thing to go for first?
