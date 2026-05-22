# Positive Instruction Framing

**Source:** Field-confirmed with Opus 4.7 -- negative directives measurably raise the rate of the behavior they warn against. Aligns with documented Anthropic prompt-engineering practice (tell the model what to do, not what to avoid).

## When

Any authored surface that instructs an agent: CLAUDE.md, `.claude/rules/`, skill and subagent definitions, memory files, subthread briefs, main-thread kickoffs. The priming effect is strongest in always-loaded surfaces (CLAUDE.md, the memory index `MEMORY.md`) -- audit those first.

Skip pure prose with no instruction in it.

## Why

A language model is a next-token predictor: text in context raises the probability of related continuations. An instruction that *names a failure mode* -- "don't guess", "never skip the tests" -- places that failure in context, and the model becomes *more* likely to produce it, not less. The negation does not cancel the priming; it rides along with it.

The corollary: anticipated *constraints* prime too. Telling a subthread it has a limited time or context budget makes it stop short and hand back unfinished work, because "running low, wrap up" becomes the anticipated continuation. Briefs that omit budget framing get the job finished.

## How

Run the directive-vs-fact test on each negation:

- **Behavioral directive** (tells the agent how to act) -- rewrite as a positive target. "Don't guess -- ask" becomes "When unsure, ask." Compliance is now the anticipated continuation.
- **Factual state description** (tells the agent how the system is) -- keep the fact, phrased positively where a positive form carries the same ground truth. "The script does not touch `/persist`" stays as information; an incident note reads "userspace failed to start", not "userspace never started" -- the tone an audit sets propagates to the next audit.

Forms that work:

- **Positive target** -- "When unsure, ask" over "Don't guess."
- **`Rejected:` specimen** -- to show an anti-pattern, label it: `Preferred: forward slashes in Bash paths. Rejected: unquoted backslashes -- Bash swallows them.` A labeled specimen reads clearer than a free-floating negative.
- **Hard constraint** -- give the positive method, then a `Rejected:` line for the tempting wrong path, so the warning still lands.
- **Subthread briefs** -- omit time/context-budget language; specify the work and a natural cut point by *work shape* instead (see `coordination-protocol.md`).

## Rules

- The acute footgun is *imperative* negations that name a model failure ("don't", "never", "do not", "cannot" + a behavior). Reframe those first.
- Mild descriptive negations ("has no", "is not") are a weak priming surface -- reframe them opportunistically when a file is touched anyway, rather than as a dedicated sweep.
- Verify by re-reading for meaning, not just by grepping the tokens away. A reframe that softens a warning into a bland description has lost ground truth -- the `Rejected:` line keeps the warning's edge.
- Apply this to memory files too: a clean brief is undone if the anti-pattern resurfaces in an always-loaded memory.

## Related Patterns

- **Collaboration Posture** -- also a positive-framing pattern; covers push-back license specifically.
- **Coordination Protocol** -- subthread briefs and kickoffs are authored surfaces this pattern governs.
