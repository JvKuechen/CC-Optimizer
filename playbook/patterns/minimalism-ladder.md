# Minimalism Ladder

**Source:** ponytail plugin (DietrichGebert), distilled to concepts -- no plugin,
no npm, no hook injector. We took the ladder, the complexity-only review lens, and
the auditable-omission discipline; we left the persona, intensity levels, and the
multi-IDE / MCP machinery in the dust.

## When

Any workspace where agents tend to over-build -- speculative abstractions,
hand-rolled stdlib, unrequested scaffolding, a dependency where one line would do.
Pairs with [Dependency Spine](dependency-spine.md) (which governs build order) and
is the complexity counterpart to an adversarial / correctness reviewer.

## How -- three liftable concepts

### 1. The decision ladder (a CLAUDE.md / rule convention)
Before writing code, walk the ladder and stop at the first rung that works:

> Does this need to exist? (YAGNI) -> does the standard library do it? -> a native
> platform feature? -> a dependency already present? -> one line? -> only then,
> the minimum that works.

### 2. A complexity dimension in your existing reviewer (not a second reviewer)
Over-engineering is a review finding, not a separate pass -- a standalone
complexity agent goes stale next to a correctness reviewer that already flags
scope-creep. Give the one reviewer an explicit over-engineering dimension with a
cut vocabulary: `delete` (speculative / unused), `stdlib` (reinvented standard
library), `native` (duplicates a dependency / platform feature), `yagni`
(single-impl abstraction / lone-caller layer), `shrink` (same logic, fewer lines).
Each finding is a deletion with its replacement. We fold this into sign 5 of
`templates/agents/adversarial-reviewer.md`.

### 3. Auditable omission (an output discipline)
Minimalism that is silent reads as an oversight. Make every deliberate cut
visible: mark a simplification in-code with a comment naming the ceiling and the
upgrade path, and end a change with 2-3 lines: `skipped: <X>, add when <Y>.`

## Rules

- **Never simplify the load-bearing.** Input validation, error handling that
  prevents data loss, security, accessibility, and explicitly requested features
  stay full. Non-trivial logic ships with one runnable self-check.
- **Exempt profiled hot paths from the ladder.** In performance-critical inner
  loops the "clever" code can be the correct code; the ladder governs
  architecture, dependencies, and scaffolding, not a profiled hot loop. (Decisive
  in perf-first workspaces.)
- **Deletion beats addition; boring beats clever** -- everywhere the two rules
  above don't apply.
- **One reviewer, an explicit complexity dimension** -- fold over-engineering into
  the correctness reviewer as a named dimension rather than standing up a second
  reviewer that drifts into disuse. Keeping the dimension explicit is what stops it
  being quietly dropped.
