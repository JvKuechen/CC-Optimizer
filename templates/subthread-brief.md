# Subthread Brief — <task or initiative name>

You are a subthread of the main thread for <workspace>. The main thread maintains the bounty board and integrates close-out reports. Get the lay of the land first, then execute the assigned task.

## LAY OF THE LAND

Read these in order before deciding scope:

1. `handoff.md` — most recent section first. Status of the broader workstream.
2. `CLAUDE.md` — settled decisions, conventions, gotchas. Note the IMPORTANT / YOU MUST lines.
3. <task-specific files: scoping doc path, target source files with their doc-comments, related tests, ADRs>

The current bounty board is embedded in the Task scope section below — the main thread rewrote it fresh for this spawn. Read source-of-truth for your task before committing to scope (the scoping doc, the existing module's doc-comments, related ADRs) — not just the one-line bounty subject.

## STAGING DISCIPLINE

Stage at commit time only:

1. `git status` to see all dirty paths.
2. Add ONLY the paths your task needs, by filename or explicit directory.
3. Rejected: `git add -A` / `git add .`.

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

1. **Task IDs shipped** — with commit hashes.
2. **Test coverage delta** — per crate/module if applicable.
3. **Open questions** — for follow-on subthreads.
4. **Surprises** — non-obvious findings worth saving as memory or settled decisions.
5. **Recommended next picks** — what should follow, and why.

For verification/audit work, include a tally table with explicit dispositions:

    | Disposition          | Count | Notes |
    |----------------------|-------|-------|
    | complete-as-claimed  |       |       |
    | fixed-now            |       |       |
    | dropped-with-rationale|      |       |

## Task scope

<paste the current bounty board — rewritten fresh by the main thread for this spawn — plus your task's row and any expansion>

What is the most correct thing to go for first?
