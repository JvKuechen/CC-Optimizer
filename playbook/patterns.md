# Optimization Patterns Toolbelt

Reusable patterns discovered across 24 workspace audits. During optimization, review this list and select applicable patterns for the target workspace.

Referenced from Phase 1.6 of the optimization checklist.

## CLAUDE.md Authoring

| Pattern | File | When to Use |
|---------|------|-------------|
| Current State Capsule | [current-state-capsule.md](patterns/current-state-capsule.md) | Active dev projects with evolving state |
| Gotchas Section | [gotchas-section.md](patterns/gotchas-section.md) | Any project with non-obvious platform/API behavior |
| Prescriptive vs Descriptive | [prescriptive-descriptive.md](patterns/prescriptive-descriptive.md) | Projects with complex architecture Claude must follow |
| Blocked Task Tracking | [blocked-task-tracking.md](patterns/blocked-task-tracking.md) | Multi-phase projects with dependencies or blockers |
| Collaboration Posture | [collaboration-posture.md](patterns/collaboration-posture.md) | Judgment-heavy or solo-owner projects — give Claude explicit license to disagree |
| Positive Instruction Framing | [positive-instruction-framing.md](patterns/positive-instruction-framing.md) | Any authored agent surface — reframe negative directives that prime the failure they warn against |

## Workflow & Process

| Pattern | File | When to Use |
|---------|------|-------------|
| Gate Pattern | [gate-pattern.md](patterns/gate-pattern.md) | Projects needing enforced review before merge/deploy |
| QA Scripts Directory | [qa-directory.md](patterns/qa-directory.md) | Projects with 5+ validation/test scripts |
| Health Check + Remediation | [health-check-remediation.md](patterns/health-check-remediation.md) | Operational/infrastructure projects |
| Isolation Bisect | [isolation-bisect.md](patterns/isolation-bisect.md) | Debugging workspaces, plugin/mod systems |
| Coordination Protocol | [coordination-protocol.md](patterns/coordination-protocol.md) | Multi-thread / multi-session / cross-workspace coordination work |
| Compaction-Safe Coordination | [compaction-safe-coordination.md](patterns/compaction-safe-coordination.md) | Long-running coordinator that delegates across compactions — keep the coordinator/executor roles surviving a context reset (SessionStart hook + commit-guard + two-strikes) |
| Dependency-Graph Conformance Ratchet | [dependency-graph-ratchet.md](patterns/dependency-graph-ratchet.md) | Machine-enforcing a convention across a codebase that starts out red — conform + gate per-unit, leaves-to-roots, warn-global/deny-per-unit |
| CI-Status Surfacing | [ci-status-surfacing.md](patterns/ci-status-surfacing.md) | Workspaces with CI gates — surface failing GitHub Actions runs at SessionStart so a red gate doesn't sit unnoticed across pushes |
| Handoff Capsule | [handoff-capsule.md](patterns/handoff-capsule.md) | Long-lived coordinator — inject a structured, schema-validated `capsule.toml` (live state) at SessionStart + a PostToolUse validator; replaces a markdown handoff. History = git log |
| Wave-Seam Session Policy | [wave-seam.md](patterns/wave-seam.md) | Multi-wave coordinator workstreams — end/compact at work-shape seams, terse notification deltas, one synthesis per seam; per-wave happy path = interview -> go wide -> spawn-seam compact -> lean integration tail; the brake on cache-read bloat now that 1M context removed forced compaction |
| Scaffold-Seam Stub Pre-Declaration | [scaffold-seam-stubs.md](patterns/scaffold-seam-stubs.md) | Fan-out waves where parallel legs would collide on a hub file (module registration, `mod.rs`, a `match`) — commit the new module stubs on `main` before spawning so each leg owns a disjoint file and branches ff-merge conflict-free |
| Visual Self-Verification Harness | [visual-self-verification.md](patterns/visual-self-verification.md) | Workspaces whose output is rendered/visual and the harness can't see it (native GPU frames, charts, PDFs, headless web) — build a render-to-artifact probe with an in-probe self-check first, so background legs self-verify and the lead eyeballs the artifact; keep tight subjective loops lead-owned |
| Model Allocation by Comparative Advantage | [model-allocation.md](patterns/model-allocation.md) | Multiple models / cross-vendor CLI / a time-limited promo model — allocate coordinator/implementer/reviewer/recon by each model's edge (one-shot economics, perishable-asset rule, cross-vendor reviewer as the offset slot) |

## Architecture

| Pattern | File | When to Use |
|---------|------|-------------|
| Config-Driven Generation | [config-driven-generation.md](patterns/config-driven-generation.md) | Multi-variant outputs (reports, parsers, templates) |
| Handler Registry | [handler-registry.md](patterns/handler-registry.md) | Multiple input formats routed to specific processors |
| Delta Polling | [delta-polling.md](patterns/delta-polling.md) | Watchers, schedulers, any periodic data processing |
| Nested Parallel Checkout | [nested-parallel-checkout.md](patterns/nested-parallel-checkout.md) | Gitea wikis, documentation repos alongside code. Variant: track content, gitignore only .git/ |
| Dependency Spine | [dependency-spine.md](patterns/dependency-spine.md) | Multi-system / monorepo workspaces where bring-up round-robins on cross-system dependencies |
| Minimalism Ladder | [minimalism-ladder.md](patterns/minimalism-ladder.md) | Workspaces where agents over-build — the YAGNI decision ladder, a complexity-only review lens (distinct from the correctness reviewer), and auditable-omission discipline; exempts profiled hot paths |

## Git Infrastructure

| Pattern | File | When to Use |
|---------|------|-------------|
| Dual Remote Push | [dual-remote-push.md](patterns/dual-remote-push.md) | Projects on both Gitea (LAN) and GitHub (WAN) |

## Deployment (Windows)

| Pattern | File | When to Use |
|---------|------|-------------|
| Silent Task Scheduler | [silent-task-scheduler.md](patterns/silent-task-scheduler.md) | Windows scheduled Python automation |
| Venv Batch Wrapper | [venv-batch-wrapper.md](patterns/venv-batch-wrapper.md) | Any Python project on Windows needing reliable venv activation |

## Hooks

| Pattern | File | When to Use |
|---------|------|-------------|
| Gitignored Search Reminder | [gitignored-search-reminder.md](patterns/gitignored-search-reminder.md) | Workspaces with gitignored dirs Claude needs to search (WS/, vendor dirs) |
| Push Review Gate | [push-review-gate.md](patterns/push-review-gate.md) | Public repos where pushes need human review before reaching remote |

## Knowledge Management

| Pattern | File | When to Use |
|---------|------|-------------|
| Knowledge Base Repo | [knowledge-base-repo.md](patterns/knowledge-base-repo.md) | Non-code repos for external software. **Ingest** static docs (PDFs, manuals) into agent-optimized markdown |
| Vendor Docs Sync | [vendor-docs-sync.md](patterns/vendor-docs-sync.md) | **Sync** evolving online docs as-is; reserve parsing for docs stable enough to stay valid |
| Code-Resident Docs | [code-resident-docs.md](patterns/code-resident-docs.md) | Internal impl-spec docs that drift from code. Move item-level "why" into doc-comments so agents must read + update it while editing |

## Safety

| Pattern | File | When to Use |
|---------|------|-------------|
| Remediation Config | [remediation-config.md](patterns/remediation-config.md) | Auto-fix tools that modify production state |
| Credential Hygiene | [credential-hygiene.md](patterns/credential-hygiene.md) | Any project with API keys, passwords, tokens |
