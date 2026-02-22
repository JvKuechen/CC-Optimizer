# Gate Pattern

**Source:** DungeonLLM

## When

Projects where code quality or architectural consistency matters enough to enforce review before proceeding. Especially useful in larger codebases (1K+ LOC) or when multiple agents are involved.

## How

Define a subagent that acts as a gate -- it reviews work and either approves or rejects with specific feedback. The workflow does not proceed until the gate passes.

```
# .claude/agents/reviewer.md
---
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---
You are a code reviewer. Review the changes for:
- Style guide compliance
- Missing error handling
- Architectural violations

Output APPROVED or REJECTED with specific line-level feedback.
```

Chain into a workflow (skill or CLAUDE.md instruction):
```
1. Implement the feature
2. Run /review (reviewer agent must APPROVE)
3. Run tests
4. Present results to user
```

## Variants

- **Finish-line ritual:** Code -> Review (gate) -> QA -> Maintainer -> Present
- **Security gate:** Security reviewer agent must approve before any file touching auth/crypto
- **Architecture gate:** Architect agent validates new module structure before implementation

## Tradeoff: Speed vs Quality

Gates measurably slow down development. The reviewer loop adds a full agent round-trip per change. In DungeonLLM this was worth it (14K LOC, 550+ tests, regressions were expensive). For smaller projects or rapid prototyping, skip gates and use manual review instead.

**Use gates when:** Regressions are costly, codebase is large, multiple agents generate code
**Skip gates when:** Prototyping, small codebase, solo rapid iteration

## Rules

- Gate agents should be read-only (no Edit/Write tools)
- Use sonnet or opus for gates, not haiku (judgment required)
- Gate rejection must include actionable feedback, not just "rejected"
- Don't gate trivial changes -- use judgment on when to invoke
