# Dependency Spine

**Source:** FortrOS

## When

Multi-system or monorepo workspaces where bring-up round-robins: you go to build
system A, discover it needs B and C first, build just enough of those, then come back.
The dependency order is real and stable but lives only in prose or in people's heads,
so it gets re-derived every session. Telltale: "partial" systems everywhere and no
single artifact that says what unblocks what.

## How

Encode the dependency graph as one tracked data file plus a deterministic checker.
Two kinds of node:

- **Build nodes** — lifted live from the build tool (`cargo metadata`, `npm ls`,
  `go list -deps`) at check time, never hand-duplicated. The build tool already owns
  the real compile-time edges; copying them by hand only invites drift.
- **System / feature nodes** — hand-authored, carrying the one field the build tool
  can't know: `test_needs` — the *minimum state of a dependency that unblocks testing
  this node*, distinct from `depends_on` (what it links or builds against).

```toml
# docs/state/build-order.toml
[key-authority]
crate = "fortros-key-rpc + fortros-key-derive"   # join key to the build-tool members
status = "partial"
depends_on = ["org-sync"]                  # often machine-knowable
test_needs = ["key-authority-phase-a"]     # hand-authored — the round-robin killer
guide = "Key Authority"
```

A checker script (e.g. `scripts/build-order.py`) topo-sorts, fails on cycles, and
asserts every build-tool member is claimed by exactly one system node (completeness
gate). The lifted graph is acyclic by construction — a cycle can only arise from a
hand-authored runtime edge, which is exactly what the checker should catch.

## Rules

- `test_needs` is the payload. `depends_on` is often machine-knowable; `test_needs`
  never is, and it is what stops the round-robin.
- Lift machine-truth edges from the build tool at check time; do not snapshot them into
  the file. Zero duplication means zero drift.
- Data is a tracked doc (match an existing `docs/state/` convention); the checker is
  dev tooling in `scripts/`. Neither belongs in a shipped crate — keeps it consistent
  with an "all-Rust components" or equivalent purity rule.
- Node IDs are crate/system names, never thread-local task IDs (this is tracked
  content — see thread-local ID hygiene in the coordination protocol).
- The completeness gate (every member claimed exactly once) catches directory-name ≠
  package-name drift before it bites.
