# Optimization Patterns Toolbelt

Reusable patterns discovered across 22 workspace audits. During optimization, review this list and select applicable patterns for the target workspace.

Referenced from Phase 1.5 of the optimization checklist.

## CLAUDE.md Authoring

| Pattern | File | When to Use |
|---------|------|-------------|
| Current State Capsule | [current-state-capsule.md](patterns/current-state-capsule.md) | Active dev projects with evolving state |
| Gotchas Section | [gotchas-section.md](patterns/gotchas-section.md) | Any project with non-obvious platform/API behavior |
| Prescriptive vs Descriptive | [prescriptive-descriptive.md](patterns/prescriptive-descriptive.md) | Projects with complex architecture Claude must follow |
| Blocked Task Tracking | [blocked-task-tracking.md](patterns/blocked-task-tracking.md) | Multi-phase projects with dependencies or blockers |

## Workflow & Process

| Pattern | File | When to Use |
|---------|------|-------------|
| Gate Pattern | [gate-pattern.md](patterns/gate-pattern.md) | Projects needing enforced review before merge/deploy |
| QA Scripts Directory | [qa-directory.md](patterns/qa-directory.md) | Projects with 5+ validation/test scripts |
| Health Check + Remediation | [health-check-remediation.md](patterns/health-check-remediation.md) | Operational/infrastructure projects |
| Isolation Bisect | [isolation-bisect.md](patterns/isolation-bisect.md) | Debugging workspaces, plugin/mod systems |

## Architecture

| Pattern | File | When to Use |
|---------|------|-------------|
| Config-Driven Generation | [config-driven-generation.md](patterns/config-driven-generation.md) | Multi-variant outputs (reports, parsers, templates) |
| Handler Registry | [handler-registry.md](patterns/handler-registry.md) | Multiple input formats routed to specific processors |
| Delta Polling | [delta-polling.md](patterns/delta-polling.md) | Watchers, schedulers, any periodic data processing |
| Nested Parallel Checkout | [nested-parallel-checkout.md](patterns/nested-parallel-checkout.md) | Gitea wikis, documentation repos alongside code repos |

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
| Gitignored Search Reminder | [gitignored-search-reminder.md](patterns/gitignored-search-reminder.md) | Workspaces with gitignored dirs Claude needs to search (wiki, docs, nested repos) |

## Safety

| Pattern | File | When to Use |
|---------|------|-------------|
| Remediation Config | [remediation-config.md](patterns/remediation-config.md) | Auto-fix tools that modify production state |
| Credential Hygiene | [credential-hygiene.md](patterns/credential-hygiene.md) | Any project with API keys, passwords, tokens |
