# Model Allocation by Comparative Advantage

**Source:** FortrOS coordinator/reviewer/implementer split (2026-06), with a Fable-5
two-week availability window and a Codex ($20) + Claude Max ($200) subscription pair.

## When

A workspace with more than one model available (multiple Claude tiers, a cross-vendor
CLI like Codex, a time-limited promo model) and distinct work roles -- coordinator,
implementer, reviewer, recon. The mistake it prevents: defaulting every role to one
"best" model, which both wastes a stronger model's edge and burns quota where a cheaper
model would do.

## How -- allocate each role to a model's comparative edge, not a global ranking

| Role | Goes to the model that is best at... | Typical pick |
|------|--------------------------------------|--------------|
| Coordinator (long-lived main session) | reasoning / judgment / orchestration | the deepest reasoner, and PERMANENT (see perishable rule) |
| Implementer -- hard/ambiguous | coding (highest SWE-bench) | the strongest one-shotter |
| Implementer -- routine/mechanical | cost / speed | a cheap workhorse |
| Reviewer (per-diff) | independent perspective + a different blind-spot set | a different VENDOR (lineage diversity) |
| Recon (survey, Explore, triage) | cheap breadth | a cheap workhorse |

## The three rules that drive the table

1. **One-shot economics put your best coder on the HARDEST problems.** A hard problem's
   true cost is not the first attempt -- it is the first attempt plus N rounds of
   `review -> return -> fix -> re-review`. The strongest one-shotter collapses N toward
   zero, so it belongs where a miss is most expensive to recover, not where the work is
   easy. This inverts the naive "save the premium model" instinct. It compounds with the
   reviewer: a higher one-shot rate turns the review pass into confirmation, not a fix loop.

2. **Comparative advantage, not a single best model.** Spend each model where its edge is
   largest. A model with the top SWE score earns the hard implementation; a deeper
   reasoner earns coordination/judgment; a cheap fast model earns routine work and recon.
   "Best overall" does not mean "best for every role."

3. **Perishable-asset rule.** When a strong model is only temporarily available, spend it
   on the work only it does best, and on roles that do not span its expiry. Put the
   perishable model on a **per-spawn-replaceable** role (implementer subagents, swapped at
   the next spawn) and keep the **permanent** model on the **long-lived** role
   (coordinator) -- so the expiry needs no mid-session model switch (which the wave-seam
   rule forbids anyway). The window expiry is also a good moment to re-check the table,
   since work TYPE often shifts at the same boundary (e.g. refactor/gates -> feature push).

## Cross-vendor reviewer = the offset slot

The reviewer is the natural place to offload onto a second subscription: it is bounded
(one diff), frequent, and parallelizable, so it offsets the most quota for the least
coordination. A different-vendor reviewer also buys lineage diversity -- it does not share
the implementer's blind spots (the [Handoff Capsule](handoff-capsule.md)'s sibling
concern: independent perspective). Empirically the bug classes split by lineage (one
vendor stronger on multi-file logic, another on security/injection), so the cross-vendor
pair catches a wider net than either alone. Keep the in-house reviewer as a fallback /
spot-check until an A/B confirms the cross-vendor one.

**With a single / cheaper reviewer, raise the reviewer's own depth rather than
having the coordinator re-verify it.** The instinct after dropping to one
reviewer is to have the coordinator independently re-check every verdict, which
spends exactly the tokens you offloaded by using the cheap reviewer (a real
symptom: running the reviewer and the coordinator's own verification in parallel
on every leg). The cheaper fix is to make the reviewer thorough: run it at high
reasoning effort by default, and feed it the worker's close-out (`--closeout`)
so its claims-cross-check runs. A reviewer that verifies its own load-bearing
claims before asserting them (a `cargo tree` before a "closure regression") is
one the coordinator can take at its word. Then let the loop carry it: when the
reviewer finds nothing and the close-out holds, fold the leg and let the test
suite confirm it on merge. When it flags something, look at that point; the
coordinator's own deeper checking is for a verdict that looks off, not for every
review. Implementer plus reviewer plus a green test run is the bar.

## Worked example (the source allocation)

Coordinator = Opus (permanent, deep judgment, dodges the expiry seam). Hard-leg
implementer subagents = Fable (top SWE, one-shots the crypto/subtle legs). Routine
implementer + recon = Sonnet (conserve the perishable model's rate budget for hard work).
Reviewer = Codex GPT-5.x (cross-vendor, security strength, offset onto the $20 sub). At
Fable expiry: hard-leg implementer -> Opus; everything else unchanged; no coordinator
switch needed.
