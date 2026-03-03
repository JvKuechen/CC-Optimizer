# Context Handoff Protocol

## Core Principle

The handoff file is a **living document**, not a one-time snapshot. Update it as you go so that a crash or unexpected session end never loses meaningful context.

## When to Create a Handoff

At the start of any non-trivial task (multi-step, multi-file, or anything that would hurt to redo):

1. Write a `handoff.md` file in the project root (or `findings/handoff.md` in the optimizer workspace)
2. Include: current goal, approach decided, key decisions made so far
3. Keep it lightweight at first — just enough to orient a fresh session

## Updating the Handoff

IMPORTANT: Update `handoff.md` progressively as you work:

- After completing a significant step (file created, decision made, problem solved)
- After the user makes a key decision that affects direction
- When context usage exceeds ~85%, do a final update and tell the user:
  ```
  /compact Focus on handoff.md for session state. Next: [describe next task]
  ```

Do NOT wait until 85% to write the first handoff. Write early, update often.

## Task List

IMPORTANT: Hydrate the task list (TaskCreate) alongside the handoff file for multi-step work. The task list survives auto-compaction and shows progress at a glance. The handoff captures context and decisions; the task list tracks how far you got.

- Create tasks when starting non-trivial work (3+ steps)
- Mark tasks in_progress/completed as you go
- After compaction, read the handoff first (goals, decisions, approach), then check TaskList to see where you left off

## Handoff File Contents

- **Date and session context** (what is being worked on)
- **Completed work** (files created/modified, with paths)
- **Current task state** (what's in progress, what's blocked)
- **Next steps** (concrete, actionable)
- **Key decisions** (anything the user decided that shouldn't be lost)
- **Resume instructions** (read this file, then do X)

## Starting a New Conversation

When starting a new conversation and a `handoff.md` exists:

1. Read it first to restore context
2. Check if it's still relevant (compare date, described task vs current ask)
3. If relevant: pick up where it left off, continue updating the same file
4. If stale: delete it and start fresh

## Staleness Check

A handoff is stale when:
- The user's current ask is unrelated to what the handoff describes
- The files/state described no longer match reality
- The user explicitly says to ignore it or start fresh

When in doubt, ask the user: "I found a handoff from [date/context]. Should I pick up from there or start fresh?"
