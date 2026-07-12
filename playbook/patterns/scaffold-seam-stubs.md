# Scaffold-Seam Stub Pre-Declaration

**Source:** CaskToCasket wave-build transcript (2026-06-21). Three waves, six parallel
worktree legs, zero merge conflicts -- because the lead committed module stubs on `main`
*before* fanning out, making each leg's file set disjoint by construction.

## When

Any wave where the lead fans independent edit legs out to parallel worktree subagents
(the coordination protocol's go-wide step). The failure mode it prevents: two legs both
need to register a new module (`pub mod x;` in `lib.rs`, a new entry in a `match`, a
shared `mod.rs`), so their branches both touch the same hub file and collide at merge --
turning "disjoint parallel work" into a manual conflict resolution.

## How

Between agreeing the wave and spawning it, the lead makes one scaffold commit on `main`:

1. **Declare every new module/registration the wave will add** -- `pub mod terrain;`,
   `pub mod geometry;`, the `match` arms, the trait the legs will implement -- in the
   hub files, pointing at stub files.
2. **Write the stub files** as compiling no-ops with a one-line doc comment naming the
   leg that will fill them and the spec section to read (`//! STUB -- Leg B fills this;
   see docs/design/meshing-spec.md section 2`).
3. **Confirm the crate compiles green** at the scaffold commit -- this is the base every
   leg branches from (worktrees branch from local `HEAD`).
4. **Fan out.** Each leg now owns the *body* of one stub file plus its own new files;
   the hub files are already correct on `main`, so no leg re-touches them. Branches
   ff-merge in any order without conflict.

The scaffold commit pairs with the leg table (capsule `active_wave`): owned-scope per
leg is exactly "the stub file(s) I was handed."

## Why it works

A merge conflict needs two branches editing the same lines. Module registration is the
usual shared-line magnet, and it is also *predictable* -- the lead knows at planning time
which modules the wave adds. Moving those edits into a single pre-wave commit removes the
magnet before any leg exists. The cost is one cheap commit; the saving is the entire
integration-tail conflict-resolution pass.

## Boundaries

- A leg that must edit a hub file *body* (not just its declaration) -- e.g. a real
  registry with ordering logic -- still collides. Either pre-stub the registry entry too
  (a `None`/`todo!()` placeholder the leg replaces in place) or sequence that leg.
- Whole-tree mechanical sweeps (format/lint combs) touch every file and cannot be made
  disjoint -- run them alone in the integration tail, never as a parallel leg.

## Variants

- Pairs with [Wave-Seam Session Policy](wave-seam.md) (the scaffold commit is step 2 of
  the seam loop, before "go wide") and the coordination protocol's disjoint-file-set rule.
