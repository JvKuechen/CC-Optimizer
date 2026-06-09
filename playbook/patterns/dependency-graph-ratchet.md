# Dependency-Graph Conformance Ratchet

**Source:** FortrOS paradigm-comb initiative

## When

You want to **machine-enforce a convention** (a paradigm, a lint posture, an architectural
rule) across a large existing codebase that does **not** currently satisfy it. You cannot
flip a strict gate (`clippy -D warnings`, an import rule, a custom lint) on the whole tree at
once -- it walls off everything. The ratchet conforms + gates incrementally, in dependency
order, so the gate goes green per-unit and never goes backwards.

This is how to *land* a [Gate Pattern](gate-pattern.md) on a codebase that starts out red.

## How

1. **Warn globally, deny per unit.** The strict gate runs in *warn / surface* mode across
   the whole tree; a unit (crate / module / package) flips to *deny* only after it's
   conformed. Enforcement is a ratchet, not a switch.
2. **Conform leaves-to-roots.** A unit isn't touched until everything it depends on is
   settled and gated, so each unit is conformed against already-conformed foundations. The
   walk and the gate-ratchet are **one pass**, not two.
3. **Calibrate the template on a model unit first.** The first unit through establishes the
   per-unit *definition-of-done* (what "conformed" means + the exact gate mechanics) that
   every later unit copies. Pick a clean, representative unit -- it sets the bar.
4. **A separate hard-gated job over the conformed set only** (no `continue-on-error`), with an
   explicit **EXTENSION POINT** -- each later unit appends one line. The whole-tree warn job
   stays for the unconformed remainder, so nothing is dark and nothing is prematurely red.
5. **The lead owns the shared gate file.** Worker legs conform their own unit (disjoint dirs,
   conflict-free) and NEVER touch the shared CI gate; the lead appends the unit centrally +
   *promptly* after each merge -- so N parallel legs don't N-way-conflict on one line, and the
   gate is never dark for a merged-but-unlisted unit.
6. **Classify before conforming, and verify the classification.** "Looks clean / has no
   obvious dependency" is not proof. Sweep *all* the relevant signals before deciding a unit's
   class -- e.g. every I/O vector (`fs`/`env`/`net`/`process`/`stderr`), not just the one
   obvious dep -- because a misclassification conforms a unit against the wrong template.

## Variants

- **Two definition-of-done templates** often emerge: a *pure* unit (zero of the banned thing)
  and an *adapter* unit (the banned thing is legitimate at the boundary -- conform the seam,
  not the loop). Calibrate one of each on a model unit; later units pick a template by class.
- **Structural vs semantic:** the gate catches *shape* (lints / types / imports). It does NOT
  catch the load-bearing axioms (idempotency, convergence, safety invariants) -- those need
  property tests + human review. A green gate means "shaped right," never "correct."
- **Preserve forward references by stubbing, don't delete them.** When conforming reveals a
  call to an unbuilt symbol, make the call real to a stub (the stub records its callers) rather
  than erasing the intent; the caller's status is then honestly "depends on a stub," not "done."
- Pairs with [Gate Pattern](gate-pattern.md), [Dependency Spine](dependency-spine.md), and
  [Compaction-Safe Coordination](compaction-safe-coordination.md) (which runs the parallel legs).
