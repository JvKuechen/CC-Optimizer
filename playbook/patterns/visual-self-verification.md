# Visual Self-Verification Harness

**Source:** CaskToCasket wave-build transcript (2026-06-21). A native Vulkan game: frames
cannot be screenshotted by an outside tool, so a background subagent could not otherwise
prove its rendering change worked. The fix -- a render-to-PNG harness -- became "the
autonomy gate": the first thing built, because it is what lets every later visual leg
self-verify headlessly.

## When

Any workspace where the agent's output is *visual or rendered* and the harness cannot see
it by default: native GPU frames, generated charts/diagrams, PDF/print layout, rendered
HTML/email, plotted data, image pipelines. The failure mode: the agent edits rendering
code, tests compile and pass, but nobody -- agent or lead -- has actually looked at the
output, so a blank frame, wrong winding, or inverted color ships green.

## How

Build a headless render-to-artifact path *first*, before the visual features that depend
on it:

1. **A probe binary/script** that exercises the real pipeline and writes a deterministic
   artifact to a known path (`artifacts/scene.png`). For GPU work, render to an offscreen
   texture and read it back; for charts, render to a file backend; for web, a headless
   screenshot.
2. **A self-check inside the probe** -- assert the cheap invariants the agent can verify
   without eyes: a center/corner pixel is the expected color, the file is non-empty, the
   backend is the intended one (CaskToCasket asserts the Vulkan adapter and fails loud on
   any other). The probe exits non-zero on failure so a background agent's gate catches it.
3. **The lead reads the actual artifact.** The Read tool renders PNGs visually -- the lead
   inspects the image before merging, catching the things a pixel assert cannot (framing,
   readability, "does it look like an island"). This is the human-in-the-loop step the
   self-check does not replace.

A background visual leg's close-out points at the artifact it wrote; the lead opens it as
part of the diff review.

## Lead-owned tight loops

When the iteration is tight and subjective -- framing, color, drag feel, "smoother but
still crisp" -- the lead drives it directly on `main` instead of delegating. The
round-trip through a worker brief loses the nuance, and a vague visual brief misfires: in
this transcript a delegated "show me the smoothing options" leg built a synthetic test
scene instead of the actual island, because the brief described the goal instead of
naming the concrete reference artifact. Rule: hand a visual worker a concrete reference
("the same island, only the grass top smoothed"), or keep the loop in the lead's hands.

## Why it works

It converts an un-observable output into a checkable artifact, which is what makes
autonomous visual work possible at all -- and it front-loads that capability so it gates
everything after. The self-check covers regressions cheaply; the lead's eyeball covers
judgment; together they keep a blank-frame-but-green from shipping.

## Variants

- Pairs with [Gate Pattern](gate-pattern.md) (the probe is the enforced gate) and
  [Wave-Seam Session Policy](wave-seam.md) (build the harness as wave 1, before the
  features that need it).
