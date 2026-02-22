# ClaudeDocs Roadmap

Last updated: 2026-02-22

## Completed

### Core Optimization
- [x] Audit all workspaces
- [x] Create .claude/settings.json with consolidated permissions
- [x] Deploy context-handoff.md and windows-shell.md rules
- [x] Evaluate/trim CLAUDE.md files
- [x] Windows compatibility checks

### Machine Setup
- [x] Deploy global permissions (~75 safe commands)
- [x] Deploy guardrail hook (blocks destructive commands)
- [x] Deploy notification hook (audio alerts)
- [x] Deploy fix-line-endings hook (PostToolUse CRLF->LF conversion)
- [x] Install LSP plugins: pyright-lsp, typescript-lsp, csharp-lsp

### Centralized Asset Sharing
- [x] Deployed shared rules to `~/.claude/rules/`
- [x] Deployed shared agents to `~/.claude/agents/`
- [x] Removed duplicate rule files from workspaces
- [x] Updated playbook to verify user-scope assets instead of copying per-project

### Fan-Out Orchestration
- [x] Core orchestrator (`fan-out/orchestrator.py`) -- cascading error recovery (haiku->sonnet->opus)
- [x] BFS discovery (`fan-out/discovery.py`) -- finds all projects across configured paths
- [x] Worker prompt template (`fan-out/workers/folder-scout.md`)
- [x] Workspace optimizer (`fan-out/optimize-workspaces.py`) -- bulk CLAUDE.md generation
- [x] Config-driven scripts -- all personal data in gitignored JSON configs

### Doc Sync & Playbook Refresh (2026-02-10)
- [x] Synced docs (removed stale iam.md, split into permissions + authentication)
- [x] Updated playbook with new doc pages (agent-teams, authentication, fast-mode, keybindings, permissions, checkpointing)
- [x] Added permissions path syntax, agent teams guidance, new hooks (TeammateIdle, TaskCompleted)
- [x] Added nested-parallel-checkout pattern to toolbelt

### Public Release Cleanup (2026-02-22)
- [x] Extracted personal data from scripts into gitignored JSON configs
- [x] Created config loader (`fan-out/config.py`) with example templates
- [x] Genericized all documentation (example.com placeholders)
- [x] Split roadmap into public (this file) and private planning file

---

## Planned

### Phase 5: Skills for Repetitive Workflows (Priority: Medium)

Candidates for shared skills:
- [ ] `/deploy` -- Deployment workflow (per-project customization via env vars)
- [ ] `/review` -- Code review checklist
- [ ] `/create-pr` -- PR creation with standard format
- [ ] `/investigate` -- Bug investigation workflow
- [ ] `/test` -- Run tests with filtered output

Design considerations:
- Skills should be generic enough to share across projects
- Use `allowed-tools` for auto-approval
- Use `disable-model-invocation: true` for side-effect workflows

---

### Phase 6: Subagents for Specialized Work (Priority: Medium)

Candidates for shared agents:
- [ ] **security-reviewer** -- Read-only, opus model, checks for vulnerabilities
- [ ] **test-runner** -- Runs tests, analyzes failures, haiku model
- [ ] **code-reviewer** -- Structured feedback, sonnet model
- [ ] **performance-analyzer** -- Identifies bottlenecks, profiles code

Design considerations:
- Restrict tools to minimum needed (allowlist)
- Use appropriate model for task complexity
- Read-only agents use `permissionMode: plan`

---

### Phase 7: Hooks for Deterministic Automation (Completed 2026-01-28)
- [x] **auto-format.py** -- PostToolUse on Write/Edit, detects project type, runs formatter
- [x] **lint-check.py** -- PostToolUse on Write/Edit, runs linter, reports issues
- [x] **test-filter.py** -- PostToolUse on Bash, summarizes test output

Deployed to `~/.claude/hooks/` alongside guardrail.py.

---

### Advanced Features (Priority: Low -- As Needed)

#### MCP Servers
- [ ] Database connections for projects with DB access
- [ ] API integrations (GitHub, Gitea, etc.)
- [ ] Document which workspaces would benefit

#### CI/CD Pipeline Templates
- [ ] Gitea Actions workflow templates (app, infra, knowledge categories)
- [ ] CI dispatcher (SSH ForceCommand allowlist for deploy operations)
- [ ] Runner setup (DinD sidecar, two-label architecture)

#### Sandboxing
- [ ] Filesystem/network isolation for sensitive projects
- [ ] Evaluate Docker-based sandbox vs native

---

## Backlog / Ideas

- [ ] Self-updating mechanism: When docs change, auto-update playbook
- [ ] Workspace health check skill: Validates optimization is intact
- [ ] Migration tool: Apply new patterns to all workspaces in batch
- [ ] Metrics: Track permission prompts, context usage, session length
- [ ] Documentation/portfolio prep fan-out for project READMEs
- [ ] Git remote setup automation (dual-remote-push pattern)
- [ ] Mass project renaming for poorly/generically named projects

---

## Notes

- Phases 5-7 are "nice to have" -- implement when specific need arises
- Advanced features require per-project evaluation
- Centralized sharing is complete -- updates to `~/.claude/` propagate to all workspaces
- Skills remain per-project (optimizer-specific workflows stay in ClaudeDocs)
