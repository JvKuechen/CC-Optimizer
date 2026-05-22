# Code-Resident Docs

## What This Is

Implementation-specific documentation — the "why is this code shaped this way" — lives in **doc-comments at the code itself**, not in a separate `docs/` spec tree. Conceptual documentation (the problem space, the big foundational tradeoffs) stays in a separate location. The two are split by a clear line, and nothing tries to be both.

The driver is **Chesterton's Fence**: when the rationale for a piece of code lives in a separate file, an agent (or human) editing that code doesn't see the rationale — doesn't know why the fence is there — and removes or breaks it. When the rationale is a doc-comment on the function, the agent *physically cannot* edit the function without reading it, and updating the comment is part of the same edit. The forcing function is the point: co-location makes "read the why" and "keep the why current" unskippable rather than aspirational.

## The Problem It Solves

A separate implementation-spec doc carries two jobs with different lifecycles:

- **Design-before-code** — a planning artifact, useful while the feature is being designed.
- **Post-implementation reference** — what the running code does and why.

One file doing both must be touched twice for every change, and the two roles drift apart whenever someone updates it for one job but not the other. Worse, the spec duplicates what the code already encodes (the schema is in the types, the lifecycle is in the functions) — so maintaining it is redundant work that gets skipped under deadline. Then the spec is wrong, and the next agent trusts it.

Symptoms in a target workspace:

- A `docs/`, `design/`, or `specs/` tree whose files describe how modules work.
- Those files are stale relative to the code (modified dates lag; described behavior doesn't match).
- Agents/contributors repeatedly re-derive design rationale because it isn't where they work.
- "Update the docs" is a separate task that gets deferred and forgotten.

## When to Apply

- The workspace has separate implementation-spec docs that duplicate code structure.
- The language has a doc-comment convention with a renderer (almost all do).
- Agents do real implementation work in the codebase, not just config.

## When to Skip

- **Conceptual docs** — tutorials, architecture overviews, "why this whole approach" — do NOT move into code. They have no single code home; they belong in a guide, ADRs, or README.
- Tiny projects where one CLAUDE.md covers everything.
- Docs describing *external* systems — that is Vendor Docs Sync / Knowledge Base Repo territory.

## The Split

The generalizable core. Two homes, divided by one question:

**Would a contributor disagree with this decision from _outside_ the code, or only _after reading_ it?**

| Kind | Example | Home |
|------|---------|------|
| Big / foundational rejection | "Postgres over Mongo", "REST not GraphQL" | Concept doc — guide page, ADR, or CLAUDE.md settled-decisions |
| Small / item-level rejection | "hex string not byte array here — the serializer caps at 32", "no retry wrapper — the caller already retries" | Doc-comment at the affected function/module |

Big rationale a newcomer would challenge before reading code → concept doc. Small rationale only visible once you are inside the function → doc-comment.

## Doc-Comment Conventions By Language

Every mainstream language has the machinery. Use the native one:

| Language | Module/file level | Item level | Renderer |
|----------|-------------------|------------|----------|
| Rust | `//!` | `///` | `cargo doc` |
| Python | module docstring | function/class docstring | Sphinx, pdoc, mkdocstrings |
| TypeScript / JS | file-top `/** */` | TSDoc / JSDoc `/** */` | TypeDoc, JSDoc |
| Go | package comment | exported-symbol comment | `go doc`, pkg.go.dev |
| Java | `package-info.java` | Javadoc `/** */` | `javadoc` |
| C# | file XML doc | `/// <summary>` | DocFX |
| Ruby | file comment | method comment | YARD, RDoc |

If the workspace already renders these to a browsable site, keep it. If not, the comments still pay off in-editor and on hover — the renderer is a bonus, not the point.

## How to Apply (migration)

Mechanical, per spec doc:

1. Take one implementation-spec doc.
2. Lift each section into the doc-comment of the module / class / function it describes, matching the existing doc-comment style in already-documented files.
3. Foundational rationale with no single code home → the concept doc / ADR.
4. `git rm` the spec doc **in the same commit** as the doc-comment additions. Splitting them re-opens the drift window.

## The Workflow It Enables

Once migrated, new design work follows:

1. **Concept doc first** — write or update the guide page / ADR: problem, alternatives, choice, why. Big rejections land here.
2. **Plan in-place** *(optional, advanced)* — write pseudocode comments directly in the target file. To keep planning artifacts off the main branch, tag each with the current commit hash and add a pre-commit hook that blocks commits where the tag still equals HEAD — so pseudocode either becomes real code in the same change or never lands. (FortrOS, the source of this pattern, calls this the HEAD-hash guard.)
3. **Implement** — replace pseudocode with real code; write a doc-comment on every public item and every non-obvious module. Small rejections go here.
4. **Land code + docs in one commit** — no separate spec artifact, no follow-up "update the spec" commit to forget.

## Enforcement

- **Rule** — a `.claude/rules/` file with `paths:` scoped to source files: "Implementation and its doc-comments land in the same commit. If a signature, invariant, or error condition changes, the comment above it changes in the same diff. Preserve rejected-alternative rationale — keep 'we ruled out X because Y' even when the code now makes the choice look obvious; the next reader needs it."
- **CI doc lint** — most renderers have a broken-link or missing-doc lint. Run it; promote warn → deny once the codebase is clean.
- **Review norm** — reject a code-only diff that breaks a documented contract.

## Related Patterns

- **Prescriptive vs Descriptive** — about what Claude must follow in CLAUDE.md; code-resident docs is about where implementation rationale lives. Complementary.
- **Gotchas Section** — workspace-level non-obvious behavior; code-resident docs is the item-level equivalent, at the code.
- **Current State Capsule** — "where is the project now" lives in CLAUDE.md or a tracker; code-resident docs is the per-item "why is this here".
