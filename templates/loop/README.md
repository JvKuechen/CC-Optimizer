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

Companion (deployed separately): `templates/codex/codex-review.sh` +
`templates/agents/adversarial-reviewer.md` -- the cross-vendor review leg the
gate requires when `gate.review = "codex"`.

## Deploy

1. Copy `hooks/*.py` to the workspace's `.claude/hooks/`.
2. `mkdir tickets/` at the repo root (tracked in git). Ensure `findings/`
   exists and is gitignored.
3. Deploy the Codex review leg (`scripts/codex-review.sh` +
   `.claude/agents/adversarial-reviewer.md`) per `templates/codex/`.
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

**Plan gate (human).** Cut the guide docs into tickets with a planning
session; the human reads and approves every ticket before it becomes
dispatchable. The ACs are the contract: one measurable end state each, an
exact `check` command, written so two agents could not disagree about
passing. The checks are the held-out oracle -- authored at planning time,
not by the worker. Ticket edits land in the reviewed diff, so a check
weakened mid-flight is visible to the reviewer.

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

**Gate (deterministic, at every stop).** In order: all AC checks exit 0 ->
tracked working tree clean (gate what will merge) -> fresh Accept from
`findings/codex-review-<ticket-id>.md` (newer than HEAD, no Reject, no
PROVISIONAL). Any failure blocks the stop and feeds the exact failure back
as next-turn guidance, including the `codex-review.sh` invocation when the
review is what's missing. Full pass flips the ticket to `review` and
releases the session.

**Merge (human or lead).** `review` tickets are ready-for-merge inventory.
Merge, then flip to `done`. The gate never merges.

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
