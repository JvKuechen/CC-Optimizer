# Monitor Templates

Reusable **monitors**: long-running watchers that wake an agent when external
state the harness can't notify on changes. Deployed to `~/.claude/monitors/` by
`deploy-user-settings.py`.

## Two kinds of monitor (don't conflate them)

- **Session/product monitors** watch the *thing being built* -- log tails,
  serial output, service health. They are domain-specific and belong IN the
  target workspace (e.g. a `scripts/monitor.sh` single-dispatch wrapper of named
  tail-and-filter pipelines). These are owned by that project, not here.
- **Agent-orchestration monitors** (this directory) watch the *agent harness
  plumbing itself* -- team inboxes, task queues, coordination state. They are
  workspace-agnostic, so they live at the user level (`~/.claude/monitors/`) and
  travel to every workspace that runs teams.

`inbox-recovery.py` is the second kind: nothing about it is fortros- or
project-specific, so keep it global rather than copying it into a workspace's
own monitor wrapper.

## Mechanism

Prefer the first-class **`Monitor` tool** with `persistent: true` -- one reviewed
command, surfaced to the agent when it fires:

```
Monitor(
    description: "team-lead inbox -- unread teammate messages",
    command: "python3 ~/.claude/monitors/inbox-recovery.py --watch",
    persistent: true,
)
```

Lessons worth inheriting from mature setups: keep ONE reviewed pipeline per
named monitor (debug once, reuse everywhere), and `--line-buffered` every `grep`
in a tail pipe (un-buffered `tr`/`grep` silently pools events for minutes).

Fallback when the `Monitor` tool isn't in play: Claude Code re-invokes an agent
when a backgrounded command **exits**, so a `--watch` that blocks until its
condition and then exits wakes the agent the same way. Either path, pair the
watcher with a deterministic processor (`--drain`) the agent runs on each wake.
For the high-water-mark bookkeeping inside a poll, see the `delta-polling`
pattern in the playbook.

## Arming is the hard part, not authoring

A monitor template is dead weight unless a deterministic moment arms it. Tie
arming to a trigger -- a `session-up` script that prints (or runs) the arm
commands, a kickoff/CLAUDE.md line, a `SessionStart` hook. Templates that exist
but are never armed look exactly like having no monitors at all.

## When NOT to use a monitor

If the harness already re-invokes you on the event (a tracked background task, a
teammate message on a *healthy* inbox), don't add a monitor -- it's redundant
polling. Monitors are for the gaps: state that changes silently.

## Inventory

### `inbox-recovery.py`

Workaround for a **dead agent-team inbox consumer**. When a long-lived lead
resumes/reattaches, its inbox RECEIVE path can silently die: teammates'
`SendMessage` still writes to the inbox file and returns a success receipt, but
the lead never ingests them (they stay `read:false`). Send still works; receive
is severed -- and silence looks identical to "teammates still working."

Diagnose by reading the `read` flags in
`~/.claude/teams/<team>/inboxes/<recipient>.json`: a clean cutover from
`read:true` to `read:false` at a resume boundary is the signature.

```
python3 ~/.claude/monitors/inbox-recovery.py --peek     # preview unread, don't consume
python3 ~/.claude/monitors/inbox-recovery.py --drain    # print + mark read
python3 ~/.claude/monitors/inbox-recovery.py --watch    # block until unread (run backgrounded)
```

Auto-detects the team when exactly one inbox matches `--to` (default
`team-lead`); pass `--team <name>` to disambiguate. It is a **stopgap** -- once
the lead restarts cleanly the real consumer rebinds; stop running it then.
Background context lives in the `agent-teams-worktree-isolation` memory.
