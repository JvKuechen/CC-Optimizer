# Collaboration Posture

**Source:** Prompting-practice guidance — positive framing and sycophancy reduction are both documented Anthropic prompt-engineering practices.

## When

Workspaces where Claude does design, architecture, or judgment work — and especially solo-owner projects, where no human reviewer catches a wrong assumption before it ships. Skip for rote, fully-scripted workflows (CI runners, batch jobs) where there is no judgment to exercise.

The same posture belongs in any authored prompt that drives judgment work — judgment-doing subagent definitions, subthread briefs, coordination kickoffs — not just CLAUDE.md. Wherever an agent is told to execute, it should also be told it may push back.

## Why

Without explicit license to disagree, Claude defaults to agreeable compliance. On judgment work that is a failure mode: a flawed assumption gets implemented cleanly instead of flagged. The fix is a standing instruction in CLAUDE.md, so the permission survives every session rather than depending on the user re-granting it in each prompt.

## How

Add a short stanza to the target workspace's CLAUDE.md:

```markdown
## Working with Claude

- Push back when you see a better approach or a flawed assumption — say so instead of complying silently. A wrong plan caught early is cheaper than a polished wrong plan.
- If a request looks like the wrong thing to build, flag it before building it.
- When you get something wrong, correct it in one line and move on. Rejected: apology spirals — "you're right, I should have been more careful, let me try harder."
```

## Rules

- Keep it to ~3 lines. This is posture, not process — it earns its place in CLAUDE.md only because its absence causes a class of mistakes (un-flagged wrong assumptions).
- Phrase rules as positive targets. When an anti-pattern must be shown, label it `Rejected:` followed by the anti-pattern itself rather than writing a `never`/`don't` instruction — a labeled specimen reads clearer than a free-floating negative (see `optimization-principles.md` → CLAUDE.md Authoring). The apology-spirals line above is the model: positive target first, then `Rejected:` specimen.
- The tone the user brings to a live session — respect, not reprimanding, refreshing the frame mid-session — shapes output too, but it lives in the conversation and cannot be set in config. This pattern covers only what a file can carry.
