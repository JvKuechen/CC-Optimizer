# Handoff Capsule

**Source:** FortrOS workflow-token review (the 91.6M cache-read coordinator transcript)

## When

Any workspace running the coordination protocol with a long-lived coordinator that
restarts, resumes, or compacts. The cost it kills: every session start re-reading (or
worse, re-deriving via git log + file sweeps) the current state.

## How

A single gitignored **`capsule.toml`** at the project root holds the live coordination
state. A `SessionStart` hook (`templates/hooks/handoff-capsule.py`) parses it, validates
the schema, renders it as markdown sections, and injects it into context on every
session start. A `PostToolUse` hook (`templates/hooks/capsule-validate.py`) re-validates
on every Write/Edit and **exits 2** (feeding the error back to the model) if the edit
produced invalid TOML or violated the schema. History is **git log**, not a prose file.

```toml
schema_version = 1
updated = "2026-06-10"
thread = "my-main"
role = """..."""              # required, non-empty
current_goal = """..."""      # required
current_state = """..."""     # required (changes most often)
active_wave = "none"          # optional
holds_and_gates = ["..."]     # optional list of strings
next_safe_action = """..."""  # required
open_followons = ["..."]      # optional list
```

Operating rules (the hook's injected header restates them every session):

- Edit fields **in place**, **once per wave seam** (wave close, direction change,
  pre-compact) -- the coordinator folds worker close-outs into that one edit. The
  validator keeps you honest. Per-step edits are churn: each Edit forces a re-read
  of the file, and the crash-safety they buy already lives in the task list +
  `git log`.
- The **coordinator is the only writer**. Workers get the capsule read-only (via
  the SessionStart injection or their brief) and report back through close-outs --
  one shared lay of the land in, one fold per seam out, no write collisions.
- Keep it **flat** (top-level keys, `"""multi-line"""` for prose, inline arrays for
  lists). Flatness is deliberate: a stray `sed` of one line stays valid TOML, where
  YAML indentation or a JSON brace would not.
- History lives in **git log**, not the capsule. The capsule is live state only.

## Why structured, not markdown

The state has known fields, so storing it as prose and hand-rolling a marker/heading
extractor recovers structure that was thrown away. A structured file gives it back:

- **Schema enforced** -- the `PostToolUse` validator is a deterministic guard (fails
  loud on a bad edit), not a self-heal nudge that silently degrades and hides drift.
- **Queryable** -- `tomllib.load(...)["next_safe_action"]` is a field read, not a regex
  against `## NEXT SAFE ACTION`.
- **The injector shrinks** -- a stdlib parse + render, not bespoke marker logic.

The one cost (a structured file is less forgiving of a sloppy in-place edit) is paid by
the validator: a malformed edit is rejected at write time and corrected, which is the
enforcement, not a regression.

## Settled design verdicts

1. **Inject on every SessionStart source** (startup, resume, compact, clear). ~1-2k
   tokens; one avoided rediscovery pass pays for weeks of injections.
2. **Coordinator-only.** The injector skips silently for subagents
   (`agent_id`/`agent_type`) and worktree cwds -- a scoped executor must not inherit the
   coordinator's NEXT SAFE ACTION. Same fail-safe posture as `sessionstart-coordinator.py`.
3. **Fail loud, not graceful.** A parse/schema error surfaces as a visible nudge at
   startup and blocks the bad write at edit time; it never silently degrades. (Reverses
   the earlier markdown design's quiet-degradation rule -- that hid drift, which cuts
   against the deterministic-guard posture.)
4. **TOML, kept flat.** Recognizable where the workspace already uses TOML for state;
   stdlib-parseable (`tomllib`, 3.11+); `"""` multi-line for prose; the most
   sed-survivable structured format.

### On the earlier "structured sidecar -- Rejected" verdict

A prior version of this pattern rejected a structured `handoff.state.toml`, reasoning
"with two state files one always goes stale." That rejection was about a SIDECAR
alongside a markdown `handoff.md` -- two files. This design is a **replacement**:
`capsule.toml` is the single state file; there is no markdown `handoff.md` to drift
against. The staleness argument required two files and no longer applies. The separate
"Rejected: an MCP server for handoff state" still holds -- the need is freshness +
schema, met by a file + stdlib parse + a validator hook, with no process or extra tool
turns.

## Variants

- Pairs with [Compaction-Safe Coordination](compaction-safe-coordination.md): the role
  re-assertion hook handles posture, this one handles state; post-compact the
  coordinator trusts the injected capsule and reads git log for history.
- Distinct from [Current State Capsule](current-state-capsule.md), which is a tracked
  CLAUDE.md section for *project* state visible to every contributor; this capsule is
  per-workstation *thread* state, gitignored.
