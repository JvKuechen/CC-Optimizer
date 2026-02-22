# Isolation Bisect

**Source:** VortexManager

## When

Debugging crashes, failures, or regressions in systems with many interacting components (mods, plugins, microservices, feature flags).

## How

Formalize a step-by-step isolation strategy and document it in CLAUDE.md or a skill.

```markdown
## Isolation Strategy

1. **Baseline:** Disable all optional components, verify system runs clean
2. **Bisect:** Enable half the components, test
3. **Narrow:** If crash, bisect the enabled half. If clean, bisect the disabled half
4. **Isolate:** Repeat until single component identified
5. **Confirm:** Enable only the suspect component, reproduce the failure

## Component Risk Matrix

| Component | Hook Type | Risk | Last Verified |
|-----------|-----------|------|---------------|
| AuthPlugin | startup | Low | 2026-01-15 |
| CacheLayer | request | Medium | 2026-01-10 |
| Analytics | async | High | 2025-12-20 |
```

## Rules

- Always establish a clean baseline first (step 1)
- Log which components are enabled/disabled at each step
- Risk matrix helps prioritize -- test high-risk components first
- Document the result: which component, root cause, fix applied
