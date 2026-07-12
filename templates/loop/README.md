# Loop kit -- verification-gated ticket loop

Turn guide/spec docs into a git-tracked ticket queue and loop a fresh Claude
Code session per ticket until a gate **you** control says done. The gate, not
the worker, decides "done": deterministic acceptance checks plus a
cross-vendor (Codex) review verdict over the cumulative diff. Runs entirely
on subscription-native primitives (interactive sessions, `claude -p`,
Stop hooks) -- no custom API harness.

Design rationale in one line: every loop tool in the wild solves
*orchestration* (pick next, retry, stall-detect) and none solves
*correctness* -- agents saturate the tests they can see while failing
held-out checks of the same spec, and more iteration widens the gap. So the
loop here is a dispatch detail; the product is the gate.

## Pieces

| File | Role |
|------|------|
| `ticket-template.toml` | Ticket schema: context, numbered machine-checkable ACs, gate config, escalation fields |
| `hooks/ticket-validate.py` | PostToolUse guard: a malformed ticket edit fails loud at edit time |
| `hooks/loop-gate.py` | Stop hook: the session cannot end while the in_progress ticket's gate is unmet |
| `approve-tickets.py` | Plan-gate driver: cross-vendor design review over each draft ticket, ACCEPT flips draft -> ready |

Companion (deployed separately): `templates/codex/codex-review.sh` +
`templates/agents/adversarial-reviewer.md` -- the cross-vendor review leg the
gate requires when `gate.review = "codex"`.

## Deploy

1. Copy `hooks/*.py` to the workspace's `.claude/hooks/`.
2. `mkdir tickets/` at the repo root (tracked in git). Ensure `findings/`
   exists and is gitignored.
3. Deploy the Codex review leg (`scripts/codex-review.sh` +
   `.claude/agents/adversarial-reviewer.md`) per `templates/codex/`, and
   copy `approve-tickets.py` to `scripts/`. Pin the review model once by
   exporting `CODEX_REVIEW_MODEL` (and optionally `CODEX_REVIEW_EFFORT`) in
   the project's `.claude/settings.json` env block -- every review and
   plan-gate leg then uses it without per-call flags. Pins are perishable
   (a review model can be withdrawn server-side mid-wave), so also set
   `CODEX_REVIEW_MODEL_FALLBACK`: the script resolves the pin against
   codex's local model cache, falls back automatically when the preferred
   model is withdrawn, and restores it when the cache lists it again.
4. Wire both hooks in `.claude/settings.json`. The Stop-hook `timeout` must
   cover the slowest AC check plus the git calls -- a 10-minute test suite
   needs more than 600:

```json
{
  "hooks": {
    "Stop": [
      {"hooks": [{"type": "command",
                  "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/loop-gate.py\"",
                  "timeout": 1800}]}
    ],
    "PostToolUse": [
      {"matcher": "Write|Edit",
       "hooks": [{"type": "command",
                  "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/ticket-validate.py\""}]}
    ]
  }
}
```

## The loop

**Plan gate (human or cross-vendor).** Cut the guide docs into tickets with
a planning session. Tickets are born `status = "draft"`; only `ready` is
dispatchable, and the plan gate is what flips draft -> ready:

- **Human form:** read and approve each draft by hand. The strongest
  held-out property; keep it for judgment-dense or novel work.
- **Cross-vendor form (automated):** `python scripts/approve-tickets.py`
  runs the Codex design review over each draft (`codex-review.sh --design`)
  and flips it to ready on a terminal `VERDICT: ACCEPT`. The design adapter
  gates the AC oracle itself -- exact, non-saturable checks two agents could
  not disagree about -- because with the human out of the per-ticket loop,
  cross-vendor scrutiny of the checks is what remains of the held-out
  property. Anything but ACCEPT stays draft, report path printed. On
  ACCEPT, a deterministic falsification pass then runs each check against
  the pre-implementation tree: an oracle must be able to fail, and a check
  that already exits 0 is a vacuous filter (cargo exits 0 on a zero-match
  test name) or an already-satisfied state -- lone passes surface as
  invariant-guard notes, an all-pass oracle holds the draft.

Either way the ACs are the contract: one measurable end state each, an
exact `check` command. A backlog stub may sit in `draft` (or `blocked`)
without ACs -- the oracle is authored at the plan gate -- but nothing
AC-less ever leaves draft: the validator requires ACs from `ready` onward,
approve-tickets refuses to flip an AC-less draft even on ACCEPT, and the
Stop gate blocks a ticket with no checks. Ticket edits land in the
reviewed diff, so a check weakened mid-flight is visible to the reviewer
-- and at merge, `git diff main...<branch> -- tickets/` empty stays the
habit.

Design docs get the same pre-implementation review: `codex-review.sh
--design docs/design/foo.md --tag foo-design` -- cross-vendor feedback
while changing is cheap, before any implementation leg is spawned.

**Dispatch (one ticket per fresh session).** Fresh context per ticket is
what keeps drift and token burn bounded. Either form works:

```bash
# headless outer loop: dispatch the next ready ticket
claude -p "Work tickets/T-001.toml: set status in_progress, implement to the
ACs, commit, run the codex review, then finish."
```

or interactively, `/goal T-001 reaches status review` on top of the same
instruction. The Stop gate enforces the exit either way; `/goal` just keeps
the turns coming without per-turn prompting.

**Gate (deterministic, at every stop).** In order: working tree clean
first, untracked files included (cheap; a never-`git add`ed source file is
the classic works-locally-broken-on-merge, and the expensive checks then
exercise exactly what merges) -> all AC checks exit 0 -> fresh verdict in
`findings/codex-review-<ticket-id>.md` (newer than the last code commit,
terminal `VERDICT: ACCEPT` or `CONDITIONAL` line -- the gate parses that
line alone, so `Rejected:` labels inside findings stay unambiguous -- and
no PROVISIONAL findings). Any failure blocks the stop and feeds the
exact failure back as next-turn guidance, including the `codex-review.sh`
invocation when the review is what's missing. Full pass flips the ticket
to `review`, records the gated commit, and releases the session.

A ticket already in `review` re-engages the gate when its session keeps
working past the flip -- a dirty tree, commits newer than the gated
commit, or a status flip that never passed the gate. This applies only
off the primary branch (default main/master, override
`LOOP_GATE_PRIMARY_BRANCH`): on the lead's checkout, `review` tickets are
the merge queue, and HEAD moves whenever anything else merges.
Bookkeeping-only commits (`tickets/`, `findings/`) never stale a verdict
or re-engage the gate.

**Merge (human or lead).** `review` tickets are ready-for-merge inventory.
At each merge: read the verdict, confirm `git diff main...<branch> --
tickets/` is empty (a worker weakening its own AC check is the one move
that defeats the gate; it is visible only if looking is a habit), commit
any uncommitted gate flip riding in the worktree, merge, flip to `done`.
The gate never merges.

**Teardown (wave close).** Remove merged worktrees, then run
`scripts/sweep-stale-brokers.sh` (banked at `templates/codex/`) -- each
Codex review leg leaves an idle app-server broker daemon behind, and they
outlive worktree removal.

## Goal mode -- state a goal, run to output

The full-auto chain composes the pieces so one stated goal runs to shipped
output with the human only at the seams:

1. **Plan.** A planning session cuts the goal into draft tickets
   (`/goal every ticket for <goal> exists in tickets/ as draft, sized to
   one session each`).
2. **Plan gate.** `python scripts/approve-tickets.py` -- cross-vendor
   approval flips drafts to ready; anything else comes back with a report
   for the planner (or you) to address.
3. **Dispatch.** Fresh session per ready ticket -- interactive (`/goal all
   tickets in tickets/ reach status review or blocked, or stop after N
   turns`) or headless (`claude -p` per ticket). The Stop gate holds every
   exit; the review leg runs inside each session in the foreground.
4. **Merge.** The lead (or you) merges `review` tickets: read the verdict,
   confirm `git diff main...<branch> -- tickets/` is empty, merge, flip to
   done.
5. Repeat until the goal's own oracle -- the E2E check or the guide's
   held-out test named when the goal was stated -- is green.

A `blocked` ticket with a filled question pierces the loop at any point:
its leg stops cleanly, and with Remote Control the question reaches your
phone. State the goal WITH its oracle up front ("done when `cargo test
--test e2e_persistence` passes on main"); a goal without a held-out check
inherits every saturation risk the per-ticket gates were built to avoid.

## Escalation

A worker that hits a decision it cannot make sets `status = "blocked"`,
fills `[blocked].question` / `options` / `recommendation`, and stops -- the
gate lets a blocked ticket through, and the validator refuses a blocked
ticket without a question. With Remote Control active
(`claude --remote-control` + "Push when Claude decides" in `/config`), the
open question reaches your phone and you answer from the Claude app.

## Circuit breakers (layered)

- `gate.max_gate_rounds` (default 5): that many blocked stops on one ticket
  flips it to `blocked` with an auto-filled question and releases the
  session -- the queue never spins on a ticket the gate keeps rejecting.
- Claude Code's built-in cap: 8 consecutive Stop-hook blocks ends the turn
  regardless.
- `/goal` accepts a turn clause ("or stop after 20 turns") as an outer bound.
- `LOOP_GATE_DISABLE=1` skips the gate entirely (manual sessions, debugging).

## Calibration

The loop earns its keep on well-specified, mechanically checkable work:
bootstrapping a new subsystem from a spec, hygiene sweeps (lint budgets,
dead-code, doc drift -- ACs are naturally exact), migration backlogs.
Hygiene tickets run solo, not concurrent with feature legs, so whole-tree
sweeps don't collide with in-flight worktrees. Extending a large existing
codebase gets sharply lower expectations -- keep those tickets small and
lean on the review gate.

Measured baseline (first trial, 2026-07-10: greenfield Rust streaming
subsystem from a settled 210-line spec, 8 tickets, all merged
review-gated, E2E oracle green): ~$124 and ~3.5h wall total. Per ticket:
$4-7 for mid-model legs on pure logic, $10-22 for top-model legs, worst
leg $36 (a mid-model on a shell-heavy Wayland integration -- 10 review
rounds). What the numbers taught:

- **Route by judgment-density, not size.** The mid model matched the top
  model at half cost on pure-logic tickets and inverted hard on the
  shell-heavy leg. Protocol/FFI/system-integration legs go to the top
  model.
- **Expect gate rounds only on leg 1.** After the harness shakes out, the
  gate goes quiet: the ticket text tells workers exactly what will be
  checked, so they self-verify before stopping. Zero gate rounds on 7 of
  8 legs; the gate's value shows up as shaped behavior and as the review
  findings (a real High in wire/authz, buffer-pool and input-lifecycle
  bugs in the compositor-adjacent legs -- all fixed pre-merge).
- **The review is waited on, not polled.** A worker that attempts to stop
  as a way to check on a backgrounded review burns a gate round per
  attempt (leg 1 burned 4 this way). The ticket's closing instruction
  must make the worker block on the review's completion.
