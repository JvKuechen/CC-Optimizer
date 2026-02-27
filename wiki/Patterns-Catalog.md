# Patterns Catalog

Reusable optimization patterns discovered across 24+ workspace audits. Full details for each pattern are in `playbook/patterns/` in the repo.

The authoritative index is `playbook/patterns.md` -- this page summarizes the catalog for quick browsing.

## CLAUDE.md Authoring

| Pattern | When to Use |
|---------|-------------|
| **Current State Capsule** | Active dev projects with evolving state -- embed a snapshot of what's done and what's next |
| **Gotchas Section** | Any project with non-obvious platform/API behavior that wastes time when forgotten |
| **Prescriptive vs Descriptive** | Projects with complex architecture Claude must follow precisely |
| **Blocked Task Tracking** | Multi-phase projects with dependencies or blockers between tasks |

## Workflow and Process

| Pattern | When to Use |
|---------|-------------|
| **Gate Pattern** | Projects needing enforced review before merge/deploy |
| **QA Scripts Directory** | Projects with 5+ validation/test scripts -- consolidate into qa/ |
| **Health Check + Remediation** | Operational/infrastructure projects that need self-healing |
| **Isolation Bisect** | Debugging workspaces, plugin/mod systems -- narrow down failures |

## Architecture

| Pattern | When to Use |
|---------|-------------|
| **Config-Driven Generation** | Multi-variant outputs (reports, parsers, templates) |
| **Handler Registry** | Multiple input formats routed to specific processors |
| **Delta Polling** | Watchers, schedulers, any periodic data processing |
| **Nested Parallel Checkout** | Gitea/GitHub wikis, documentation repos alongside code. Variant: track content, gitignore only .git/, post-commit hook syncs |

## Git Infrastructure

| Pattern | When to Use |
|---------|-------------|
| **Dual Remote Push** | Projects on both Gitea (LAN) and GitHub (WAN) -- single `git push` hits both |

## Deployment (Windows)

| Pattern | When to Use |
|---------|-------------|
| **Silent Task Scheduler** | Windows scheduled Python automation (no popup windows) |
| **Venv Batch Wrapper** | Any Python project on Windows needing reliable venv activation |

## Hooks

| Pattern | When to Use |
|---------|-------------|
| **Gitignored Search Reminder** | Workspaces with gitignored dirs Claude needs to search (WS/, vendor dirs). PostToolUse on Grep nudges Claude to re-search with explicit paths. Note: wiki/ is now tracked and doesn't need this. |
| **Push Review Gate** | Public repos where pushes need human review. PreToolUse hook on Bash blocks `git push`, generates consolidated diff review, user executes via `!` command. |

## Knowledge Management

| Pattern | When to Use |
|---------|-------------|
| **Knowledge Base Repo** | Non-code repos for external software. **Ingest** static docs (PDFs, manuals) into agent-optimized markdown. Three-layer pipeline: Import/ (raw) -> docs/ (parsed) -> wiki/ (verified) |
| **Vendor Docs Sync** | **Sync** evolving online docs as-is via manifest-based delta sync. Don't parse what will change next week |

### Sync vs Ingest

The key decision when adding external documentation to a workspace:

- **Sync** -- Docs evolve (weekly/monthly updates), already machine-readable (markdown, HTML). Mirror as-is with delta sync. Example: Claude Code docs, framework docs, SaaS API docs.
- **Ingest** -- Docs are static (ships with installer, one version), not machine-optimized (scanned PDFs, Word docs). Parse and restructure into agent-friendly markdown. Worth the effort because content is stable and raw format is hostile to agents.

Rule of thumb: if the vendor has a docs website with a sitemap, sync it. If the vendor ships PDFs with the installer, ingest them.

## Safety

| Pattern | When to Use |
|---------|-------------|
| **Remediation Config** | Auto-fix tools that modify production state -- needs guardrails |
| **Credential Hygiene** | Any project with API keys, passwords, tokens (always applicable) |
