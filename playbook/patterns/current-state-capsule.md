# Current State Capsule

**Source:** DungeonLLM

## When

Active development projects where context changes between sessions. Especially useful when multiple features are in-flight or the project has complex state.

## How

Add a `## Current State` section at the top of CLAUDE.md (below purpose/stack). Update it at the end of each session or when major milestones complete.

```markdown
## Current State

**Active branch:** feature/companion-ai
**Last session:** Implemented companion dialogue system, 3 tests failing in combat integration
**Blocked:** Waiting on Groq API rate limit increase for batch testing
**Next:** Fix combat integration tests, then merge to main
```

## Rules

- Keep to 4-6 lines max
- Facts only, no narrative
- Update before compaction/handoff (pairs with context-handoff rule)
- Delete stale capsules when resuming -- always write fresh
