# Workspace Optimization Playbook

Last updated from docs: 2026-02-22
Docs version baseline: sitemap lastmod dates from `docs/manifest.json`

---

## Pre-flight: Machine Setup (once per machine)

- [ ] Set git to use LF line endings: `git config --global core.autocrlf false && git config --global core.eol lf`
- [ ] Raise output token limit: add `export CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000` to `~/.bashrc` (default 32000 truncates large file reads and multi-file responses)
- [ ] Run `python templates/deploy-user-settings.py` to deploy global permissions + hooks + notifications
- [ ] Verify `~/.claude/settings.json` has `permissions`, `hooks.PreToolUse` (guardrail), `hooks.PostToolUse` (line endings), and `hooks.Notification` (audio alert) sections
- [ ] Verify `~/.claude/hooks/guardrail.py` exists
- [ ] Verify `~/.claude/hooks/fix-line-endings.py` exists (converts CRLF to LF after Write/Edit)
- [ ] Restart any active Claude Code sessions (hooks are snapshotted at session start)
- [ ] Test notification: start a session and wait for a permission prompt -- should hear two tones
- [x] Install LSP plugins (global -- available in all workspaces) — **DONE 2026-01-28**
- [x] Deploy shared rules and agents to user scope — **DONE 2026-01-28**

### LSP Plugin Setup (Complete)

All three LSP plugins are installed at user scope:
- `pyright-lsp` — Python projects
- `typescript-lsp` — JS/TS projects
- `csharp-lsp` — .NET projects

No PowerShell LSP plugin exists in the official marketplace. Rust (`rust-analyzer-lsp`) and Go (`gopls-lsp`) available if needed later.

### Shared Assets at User Scope (Complete)

These assets are deployed to `~/.claude/` and automatically available in ALL workspaces:

**Rules** (`~/.claude/rules/`):
- `context-handoff.md` — Context handoff protocol for long sessions
- `windows-shell.md` — Windows-specific shell rules (paths, null device, ASCII only)

**Agents** (`~/.claude/agents/`):
- `docs-reference` — Haiku agent for quick doc lookups (points to CC-Optimizer/docs/en/)
- `workspace-analyzer` — Sonnet agent for read-only workspace audits

When you update these files in `~/.claude/`, all workspaces benefit immediately. No per-workspace copies needed.

## Feature Layering and Context Cost

### Precedence rules
- CLAUDE.md files: **additive** (all levels contribute)
- Skills and subagents: **override by name** (managed > user > project for skills; managed > CLI flag > project > user > plugin for subagents)
- MCP servers: **override by name** (local > project > user)
- Hooks: **merge** (all registered hooks fire for matching events)

### Context cost awareness
| Feature | When loaded | Context cost |
|---------|-------------|-------------|
| CLAUDE.md | Every request | Keep small (<500 lines) |
| Rules (.claude/rules/) | When editing matching files | Low (path-scoped) |
| Skills | On-demand when invoked | Zero until invoked |
| Skills with `disable-model-invocation: true` | Only when user invokes | Zero passively |
| MCP tool definitions | Session start | Up to 10% of context |
| MCP with tool search | On-demand | Defers beyond 10% threshold |
| Subagents | Fresh context per spawn | Separate from main window |
| Hooks (command) | N/A | Zero tokens (shell scripts) |
| Hooks (prompt/agent) | When triggered | Uses tokens per invocation |

---

## Pre-flight: Per Optimization

- [ ] Run `/sync-docs` to ensure local documentation is current
- [ ] Open target workspace with `--add-dir` flag: `claude --add-dir /path/to/target`

---

## Pre-flight: Moving a Workspace

Sessions are stored in `~/.claude/projects/` keyed by the **encoded workspace path** (e.g., `C--Apps` for `C:\Apps`). When you move a workspace folder, `/resume` will show no history because the path changed.

**To preserve session history after a move:**

1. Move the workspace folder to its new location
2. Find the old session directory: `ls ~/.claude/projects/` (look for the old path encoding)
3. Rename it to match the new path encoding:
   ```
   # Example: C:\Apps -> ~/claudes\work\Apps
   # Old key: C--Apps
   # New key: C--Users-<username>-claudes-work-Apps
   mv ~/.claude/projects/C--Apps ~/.claude/projects/C--Users-<username>-claudes-work-Apps
   ```
4. Verify: open Claude Code in the new location and run `/resume` to confirm sessions appear

**Path encoding rules:** Replace `\` and `/` with `-`, remove drive colon (e.g., `C:\` becomes `C-`).

---

## Phase 1: Audit (Read-Only)

### 1.1 Identify the workspace type
- [ ] **Code repo** -- standard software project (build/test/deploy)
- [ ] **Knowledge base repo** -- documents external software the team uses but doesn't develop (see `patterns/knowledge-base-repo.md`). If yes: skip build/test/lint below, follow the KB repo pattern instead (Import/ -> docs/ -> wiki/ pipeline, contradiction resolution, helpdesk integration)

### 1.2 Identify the stack (code repos)
- [ ] Language(s) and framework(s)
- [ ] Build system (npm, cargo, go, gradle, make, etc.)
- [ ] Test runner (jest, pytest, go test, cargo test, etc.)
- [ ] Linter/formatter (eslint, prettier, black, rustfmt, etc.)
- [ ] Deployment method (if applicable)

### 1.3 Check existing Claude config
- [ ] `CLAUDE.md` — exists? Line count? Quality?
- [ ] `.claude/settings.json` — exists? What permissions are configured?
- [ ] `.claude/settings.local.json` — exists?
- [ ] `.claude/rules/` — exists? What rules?
- [ ] `.claude/skills/` — exists? What skills?
- [ ] `.claude/agents/` — exists? What agents?
- [ ] `.mcp.json` — exists? What servers?
- [ ] Hooks configured in settings?

### 1.4 Check other AI tool configs (port useful content)
- [ ] `.cursorrules` or `.cursor/rules/`
- [ ] `.github/copilot-instructions.md`
- [ ] Any custom AI instructions in README or docs

### 1.5 Check auto memory
- [ ] Does `~/.claude/projects/<project>/memory/` exist?
- [ ] If so, review `MEMORY.md` for stale or misleading content from prior sessions
- [ ] Check for misdirected writes (documentation content that belongs in actual docs, not memory)
- [ ] Clean or delete stale entries -- they load into every session

### 1.6 Select applicable patterns
- [ ] Review `playbook/patterns.md` toolbelt
- [ ] Check each pattern's "When" section against this workspace
- [ ] Note which patterns to apply (record in findings file)
- [ ] **Credential hygiene** is always applicable -- check for exposed secrets
- [ ] If identified as KB repo in 1.1: apply **Knowledge Base Repo** pattern (`patterns/knowledge-base-repo.md`)
- [ ] Check if project has external documentation needs: **evolving docs** (online, changes regularly) = sync as-is (`patterns/vendor-docs-sync.md`); **static docs** (PDFs, installer manuals, pinned version) = ingest into agent-optimized markdown (`patterns/knowledge-base-repo.md`). If no official source found, ask the user

### 1.7 Check git remote configuration
- [ ] `git remote -v` -- what remotes exist?
- [ ] Every project should have a primary remote as `origin`
- [ ] Does the project need additional remotes? (mirror, backup, portfolio)
  - If yes: check repo privacy (`gh repo view --json isPrivate`). Sync only to private unless intentionally public.
  - Apply **Dual Remote Push** pattern (see `patterns/dual-remote-push.md`): add second remote as additional push URL on `origin`
- [ ] Verify `main` branch tracks `origin`

### 1.8 Per-project feature decisions
- [ ] **MCP servers** -- Does the project use a database, API, or service Claude should connect to directly?
  - HTTP transport is now default, SSE is deprecated
  - MCP scopes: `local` (project-private, default), `user` (cross-project), `project` (shared `.mcp.json`)
  - MCP connections can fail silently mid-session -- check with `/mcp`
  - `MAX_MCP_OUTPUT_TOKENS` (default 25000), warning threshold at 10000
  - Plugin-provided MCP servers auto-start when plugin is enabled
  - **Windows: Python MCP servers need `cmd /c` wrapper.** Node.js `spawn()` cannot resolve the Windows Store Python alias directly. Use `"command": "cmd", "args": ["/c", "python", "-m", "package_name"]` instead of `"command": "python"`. Also verify the package has a `__main__.py` (some don't -- add a shim: `from package import main; main()`)
- [ ] **MCP Tool Search** -- If project has many MCP tools, enable dynamic loading (`ENABLE_TOOL_SEARCH=auto`). Loads up to 10% of context, defers rest. Only Sonnet 4+/Opus 4+, not Haiku
- [ ] **LSP plugin** -- What language(s)? Install the matching code intelligence plugin. Gives Claude type errors, go-to-definition, find-references via LSP tool
- [ ] **Chrome integration** -- Does the project have a web UI Claude should test?
- [ ] **Sandboxing** -- Does the project handle sensitive data that needs filesystem/network isolation?
  - `/sandbox` enables bash command isolation
  - Settings: `sandbox.enabled`, `sandbox.autoAllowBashIfSandboxed`, `sandbox.network.allowedDomains`
  - Claude can only write to the folder where it was started and subfolders (read outside is OK)
- [ ] **Fan-out candidates** -- Are there bulk operations (migrations, refactors) that benefit from parallel headless runs?
- [ ] **Checkpointing awareness** -- Note Esc+Esc for rewind menu and targeted "summarize from here" for context recovery
- [ ] **Fast mode** -- Is this workspace used for interactive dev? Note `/fast` toggle (same Opus 4.6 model, faster output)
- [ ] **Effort level** -- For Opus 4.6: `effortLevel` setting or `CLAUDE_CODE_EFFORT_LEVEL` (`low`/`medium`/`high`). `MAX_THINKING_TOKENS` is ignored on Opus 4.6 except when set to 0
- [ ] **1M context** -- Both Opus 4.6 and Sonnet 4.6 support 1M tokens. Standard rates until 200K, then long-context pricing. `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` to disable
- [ ] **Task list** -- Replaces old TODO list. `Ctrl+T` toggles view. `CLAUDE_CODE_TASK_LIST_ID` to share across sessions. `CLAUDE_CODE_ENABLE_TASKS=false` to revert
- [ ] **Session mobility** -- `/desktop` (hand off to Desktop app), `/teleport` (resume web session), `--from-pr` (resume PR-linked session), `--remote` (create web session)
- [ ] **CI resilience** -- `--fallback-model` for automatic model fallback when primary is overloaded (print mode only)
- [ ] **Keybindings** -- Does the team need custom shortcuts? Note `/keybindings` creates `~/.claude/keybindings.json`
- [ ] **Authentication** -- For Teams/Enterprise: verify auth method. Note `apiKeyHelper` setting for custom credential scripts

---

## Phase 2: Fix Permission Friction (Highest Priority)

### 2.1 Create or update `.claude/settings.json`
- [ ] Allow build commands: `Bash(<build-tool> *)`
- [ ] Allow test commands: `Bash(<test-runner> *)`
- [ ] Allow lint/format: `Bash(<linter> *)`, `Bash(<formatter> *)`
- [ ] Allow git read operations: `Bash(git log *)`, `Bash(git diff *)`, `Bash(git status *)`
- [ ] Allow git write operations: `Bash(git add *)`, `Bash(git commit *)`, `Bash(git checkout *)`
- [ ] Allow common safe tools: `Bash(ls *)`, `Bash(curl *)`, `Bash(cat *)`, etc.
- [ ] Deny destructive git: `Bash(git push --force *)`, `Bash(git reset --hard *)`
- [ ] Deny sensitive files: `Read(.env)`, `Read(.env.*)`, `Read(~/.ssh/**)`, `Read(~/.aws/**)`

### 2.2 Recommend user-level settings
- [ ] Point user to `templates/user-settings.json` for global safe defaults
- [ ] Explain: user settings apply to ALL projects, eliminating per-project friction

### 2.3 Verify guardrail hook is active
- [ ] Confirm `~/.claude/settings.json` has PreToolUse hook pointing to `guardrail.py`
- [ ] Hook blocks: docker volume/system destruction, broad rm -rf, git force-push, disk format, `> nul`
- [ ] Hook is deterministic (Python script, zero tokens, can't be reasoned around)
- [ ] If user hasn't set up global hooks yet, recommend copying from this workspace's config

### 2.4 Use correct permission path syntax
- [ ] Read/Edit rules follow gitignore spec with 4 path types:
  - `//path` -- Absolute from filesystem root (`Read(//Users/alice/secrets/**)`)
  - `~/path` -- From home directory (`Read(~/Documents/*.pdf)`)
  - `/path` -- Relative to settings file (`Edit(/src/**/*.ts)`)
  - `path` or `./path` -- Relative to cwd (`Read(*.env)`)
- [ ] IMPORTANT: `/Users/alice/file` is NOT absolute -- use `//Users/alice/file`
- [ ] `*` matches single directory; `**` matches recursively
- [ ] Use `Task(AgentName)` in deny/allow to control subagent access (e.g., `Task(Explore)`, `Task(Plan)`, `Task(my-custom-agent)`)
- [ ] Bash pattern security: argument matching is fragile (options before URL, variables, extra spaces can bypass). For network control, prefer WebFetch domain restrictions or PreToolUse hooks
- [ ] Bash is shell-operator-aware: `Bash(safe-cmd *)` won't permit `safe-cmd && other-cmd`
- [ ] WebFetch alone doesn't prevent network access if Bash is allowed (curl/wget bypass it)
- [ ] For Teams/Enterprise: check managed settings (`C:\Program Files\ClaudeCode\managed-settings.json`)
- [ ] Managed-only settings: `disableBypassPermissionsMode`, `allowManagedPermissionRulesOnly`, `allowManagedHooksOnly`
- [ ] Server-managed settings (beta): Teams/Enterprise can push settings from Claude.ai web interface, polled hourly

### 2.5 Add settings schema and permission modes
- [ ] Add `"$schema": "https://json.schemastore.org/claude-code-settings.json"` to `.claude/settings.json` for editor autocomplete
- [ ] Know the 5 permission modes: `default`, `plan` (read-only), `acceptEdits`, `dontAsk` (auto-deny unless pre-approved), `bypassPermissions`
- [ ] `dontAsk` mode: auto-denies tools unless pre-approved via `/permissions` or `permissions.allow` rules -- good for locked-down workflows
- [ ] Set default mode via `permissions.defaultMode` in settings

---

## Phase 3: Optimize CLAUDE.md

### 3.1 Content audit
- [ ] Under 500 lines? If not, identify what to move out
- [ ] Each line passes: "Would removing this cause mistakes?" — if not, cut it
- [ ] No file-by-file descriptions (Claude discovers these)
- [ ] No generic best practices (Claude already knows)
- [ ] No tutorials or explanations (not needed at runtime)
- [ ] No frequently-changing information (goes stale)

### 3.2 Add what's missing
- [ ] Build/test/lint commands (exact commands, not descriptions)
- [ ] Code style rules that differ from language defaults
- [ ] Repository workflow (branch naming, PR conventions)
- [ ] Architectural decisions Claude can't infer from code
- [ ] **Gotchas section** — non-obvious platform/API behavior (see patterns/gotchas-section.md)
- [ ] Environment requirements
- [ ] **Business context** — domain rules Claude needs for correct decisions (keep terse)
- [ ] Apply selected patterns from Phase 1.4 (current-state-capsule, blocked-task-tracking, etc.)

### 3.3 Use imports
- [ ] `@README.md` for project overview (don't duplicate)
- [ ] `@package.json` or equivalent for available commands
- [ ] `@docs/CONTRIBUTING.md` if it exists

### 3.4 Port content from other AI configs
- [ ] Migrate useful rules from .cursorrules / copilot-instructions.md
- [ ] Discard rules that are obvious or language-default

---

## Phase 4: Add Path-Scoped Rules

### 4.1 Verify user-scope rules are present
- [ ] Confirm `~/.claude/rules/context-handoff.md` exists (deployed during machine setup)
- [ ] Confirm `~/.claude/rules/windows-shell.md` exists (deployed during machine setup)
- [ ] If missing, run machine setup again or copy from CC-Optimizer `.claude/rules/`

### 4.2 Create project-specific rules
- [ ] Identify logical groupings (API, frontend, testing, database, etc.)
- [ ] Create rules with `paths:` frontmatter scoping them to relevant file patterns
- [ ] Only create project-specific rules — shared rules come from user scope

### 4.3 Common rule patterns
```yaml
# Example: API rules
---
paths:
  - "src/api/**/*.ts"
  - "routes/**/*.ts"
---
[API-specific conventions]
```

```yaml
# Example: Test rules
---
paths:
  - "**/*.test.*"
  - "**/*.spec.*"
  - "tests/**"
---
[Testing conventions]
```

---

## Phase 5: Add Skills for Repetitive Workflows

### 5.1 Identify candidates
- [ ] Deployment workflow → `/deploy` skill
- [ ] Code review checklist → `/review` skill
- [ ] PR creation → `/create-pr` skill
- [ ] Bug investigation → `/investigate` skill
- [ ] **Docs sync or ingest** -- Determine which approach fits the project's external documentation:
  - **Evolving docs** (online, machine-readable, changes regularly): create a `/sync-docs` skill with manifest-based delta sync. Mirror as-is -- don't parse what will change next week. See `patterns/vendor-docs-sync.md`
  - **Static docs** (PDFs, .docx, ships with installer, pinned version): create an `/ingest-docs` skill that parses into agent-optimized markdown. Worth the effort because the content is stable and the raw format is hostile to agents. See `patterns/knowledge-base-repo.md`
  - If no official online source is found, ask the user -- they may know of internal mirrors or have offline copies
- [ ] **Knowledge base pipeline** (KB repos only) → `/ingest-docs`, `/update-wiki`, `/search-helpdesk` skills (see `patterns/knowledge-base-repo.md`)
- [ ] Any workflow the team does repeatedly

### 5.2 Skill design guidelines
- Use `disable-model-invocation: true` for workflows with side effects (deploy, release)
- Use `allowed-tools` to auto-approve tools the skill needs
- Use `context: fork` for isolated analysis tasks
- Use `!`command`` syntax for dynamic context (git branch, PR diff, etc.)
- Keep SKILL.md focused; put details in supporting files

---

## Phase 6: Add Subagents for Specialized Work

### 6.1 Common subagent patterns
- [ ] **Security reviewer** — Read, Grep, Glob only. Model: sonnet/opus. Read-only.
- [ ] **Test runner** — Read, Bash, Grep. Model: haiku. Runs and analyzes tests.
- [ ] **Code reviewer** — Read, Grep, Glob. Provides structured feedback.
- [ ] **Performance analyzer** — Read, Grep, Bash. Identifies bottlenecks.

### 6.2 Subagent design guidelines
- Use `tools:` to restrict to minimum needed (allowlist)
- Use `model: haiku` for speed on simple tasks
- Use `model: opus` for complex reasoning (security, architecture)
- Use `permissionMode: plan` for read-only agents
- Use `memory: user|project|local` for persistent cross-session learning (auto-includes MEMORY.md, good for code-reviewer/workspace-analyzer agents)
- Use `isolation: worktree` for code-modifying agents (auto-creates isolated git worktree, auto-cleans if no changes)
- Use `background: true` to force background execution
- Use `skills:` to preload skills into subagents (not inherited from parent, full content injected at launch)
- Use `mcpServers:` to give subagents their own MCP connections (reference by name or provide inline definitions)
- Subagents can be resumed with full history (transcripts at `~/.claude/projects/{project}/{sessionId}/subagents/`)
- Subagents support auto-compaction at ~95% capacity (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` to customize)

### 6.3 CLI and CI subagent patterns
- [ ] `--agents` flag: define subagents via JSON at launch (session-scoped, not saved to disk). Useful for CI/CD and testing
- [ ] `--tools` flag: restrict which built-in tools Claude can use (`""` = none, `"default"` = all, `"Bash,Edit,Read"` = specific)
- [ ] `Task(agent_type)` in `tools:` field controls which subagent types can be spawned when using `claude --agent`
- [ ] SubagentStart/SubagentStop hooks for lifecycle automation (setup/teardown, logging)
- [ ] Subagent scope priority: CLI flag (1, highest) > Project (2) > User (3) > Plugin (4, lowest)

### 6.4 Consider agent teams for parallel inter-agent work
- [ ] Agent teams are experimental (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` in settings.json `env`)
- [ ] Use when: teammates need to share findings, challenge each other, coordinate independently
- [ ] Use subagents when: only the result matters, work is sequential, same-file edits
- [ ] Key concepts: team lead (coordinator), teammates (independent instances), shared task list, mailbox
- [ ] Display modes: `teammateMode` setting or `--teammate-mode` flag: `auto` (default), `in-process`, `tmux`
- [ ] Delegate mode: restricts lead to coordination-only (Shift+Tab to toggle)
- [ ] Plan approval: teammates can be put in plan mode, work read-only until lead approves
- [ ] Task dependencies: pending tasks with unresolved deps can't be claimed. File locking prevents race conditions
- [ ] **Windows limitation**: split-pane mode NOT supported on Windows Terminal, VS Code terminal, or Ghostty
- [ ] Token cost: ~7x more tokens than standard sessions when teammates run in plan mode

---

## Phase 7: Add Hooks for Deterministic Automation

### 7.1 Hook types
- [ ] `type: "command"` -- Shell command. Zero tokens. Exit code 0 = success, 2 = block. Use for deterministic automation
- [ ] `type: "prompt"` -- Single-turn LLM evaluation (Haiku by default, override with `model` field). Returns `{ok: true/false, reason: "..."}`. Use for judgment-based quality gates without full agent overhead
- [ ] `type: "agent"` -- Multi-turn agent with tool access (Read, Grep, Glob). Up to 50 turns, 60s default timeout. Use for codebase-aware verification (e.g., "did the agent actually run the tests?")
- [ ] Choose wisely: `command` for speed/determinism, `prompt` for simple judgment, `agent` for complex verification

### 7.2 Common hook patterns
- [ ] **Gitignored search reminder** -- PostToolUse on Grep, reminds Claude to search gitignored dirs (wiki, docs, nested repos). See `patterns/gitignored-search-reminder.md`
- [ ] **Auto-format on save** -- PostToolUse on Write/Edit, runs formatter
- [ ] **Lint on save** -- PostToolUse on Write/Edit, runs linter
- [ ] **Filter test output** -- PreToolUse on Bash for test commands, reduces tokens
- [ ] **Block dangerous commands** -- PreToolUse on Bash, exit code 2 to block
- [ ] **Audit config changes** -- ConfigChange event for compliance logging, can block unauthorized modifications
- [ ] **Pre-compact context preservation** -- PreCompact event to save critical state before compaction
- [ ] **Session lifecycle** -- SessionStart for environment setup, SessionEnd for cleanup/logging
- [ ] **Input modification** -- PreToolUse `updatedInput` can modify tool input before execution (combine with `allow` to auto-approve)

### 7.3 Hook design guidelines
- `command` hooks run outside the LLM (zero token cost). `prompt`/`agent` hooks use tokens
- Use exit code 0 for success, 2 for blocking errors
- Default timeouts: `command` 600s (10 min), `prompt` 30s, `agent` 60s. Set explicit timeout for fast hooks
- Hooks run in parallel -- don't create order dependencies
- Hook snapshot security: hooks are captured at session start. External edits trigger a warning requiring `/hooks` review
- Use `statusMessage` field for custom spinner text while hook runs
- Use `once: true` for hooks that should run only once per session (skills only)
- Use `async: true` for background command hooks (output delivered on next turn via `systemMessage`)
- Use `additionalContext` on PreToolUse/PostToolUse/SessionStart/SubagentStart to inject context
- Hooks can be defined in skill/agent YAML frontmatter (scoped to component lifecycle)

### 7.4 Hook events reference
All events: PreToolUse, PostToolUse, PostToolUseFailure, PreCompact, PermissionRequest, UserPromptSubmit, Notification, Stop, SessionStart, SessionEnd, ConfigChange, WorktreeCreate, WorktreeRemove, SubagentStart, SubagentStop, TeammateIdle, TaskCompleted

### 7.5 Public repo commit lock
- [ ] Check `git remote -v` for public hosting (github.com, gitlab.com, etc.)
- [ ] LAN-only remotes (private IPs, `.local` domains, internal Gitea) are considered private -- skip
- [ ] If public remote found: ask user if repo is public
- [ ] If public: create `.public-repo` marker (tracked), install pre-commit hook (blocks `git commit` without `PUBLIC_REPO_VERIFIED=1`), add `scripts/verified-commit.sh` wrapper, document workflow in CLAUDE.md
- [ ] Add `Bash(scripts/verified-commit.sh *)` to `.claude/settings.json` allow list
- [ ] Hook content: see CC-Optimizer `scripts/setup.py` (`PRE_COMMIT_HOOK`, `COMMIT_MSG_HOOK`)

### 7.6 Agent team quality gate hooks
- [ ] `TeammateIdle` -- Runs when a teammate is about to go idle. Exit code 2 sends feedback and keeps teammate working. Command-only
- [ ] `TaskCompleted` -- Runs when a task is being marked complete. Exit code 2 prevents completion and sends feedback. Supports command, prompt, and agent types
- [ ] `TaskCompleted` fires for explicit TaskUpdate calls AND when teammates finish with in-progress tasks
- [ ] `SubagentStart`/`SubagentStop` -- Lifecycle hooks for subagent setup/teardown. SubagentStop includes `agent_transcript_path` and `last_assistant_message`

---

## Phase 8: Windows Compatibility

### 8.1 Verify Windows shell rules are present
- [ ] Confirm `~/.claude/rules/windows-shell.md` exists (deployed during machine setup)
- [ ] Key rules enforced: forward slashes in Bash, `/dev/null` not `nul`, `python` not `python3`, ASCII only in code
- [ ] If missing, run machine setup again or copy from CC-Optimizer `.claude/rules/`

### 8.2 Verify scripts are cross-platform
- [ ] No `grep -P`, `mapfile`, `readarray`, `sed -i` in any scripts
- [ ] Python scripts use `pathlib.Path` not string concat with backslashes
- [ ] No reliance on `chmod`, `ln -s`, or Unix permissions

### 8.3 Enforce LF line endings
- [ ] Verify global git config: `git config --global core.autocrlf` should be `false`, `git config --global core.eol` should be `lf`
- [ ] Add `.gitattributes` with `* text=auto eol=lf` (per-repo reinforcement)
- [ ] Verify `fix-line-endings.py` PostToolUse hook is active (deployed during machine setup)
  - This is the **real fix** -- `.gitattributes` and git config only normalize at git boundaries, but the Write tool produces CRLF on disk. The hook converts immediately after every Write/Edit.
  - Skips binary files (null byte detection) and CRLF-required types (.bat, .cmd, .ps1, .psm1, .psd1)
  - CLAUDE.md instructions cannot fix this -- the Write tool ignores them
- [ ] For repos deploying to Linux: add explicit rules for shell/config files (see infra-config `.gitattributes`)
- [ ] Run `git add --renormalize .` if converting an existing repo from CRLF to LF

### 8.4 Check for existing damage
- [ ] Look for `nul` files in workspace root (created by bad `> nul` redirects in Git Bash)
- [ ] Look for `tmp/claude-*-cwd` files (created by broken path quoting)
- [ ] Clean up nul files: `python scripts/delete-nul-files.py <workspace-path>` (uses Win32 DeleteFileW API -- CMD `del` and `rm` cannot delete reserved names from Git Bash)

---

## Phase 9: Report and Handoff

- [ ] Summarize all changes made
- [ ] Explain rationale for each addition
- [ ] Note anything that needs user customization (env vars, project-specific paths)
- [ ] Recommend user-level settings if not already configured
- [ ] Confirm no `nul` files or `tmp/claude-*-cwd` debris left behind

---

## Deprecations (as of Feb 2026)

- `includeCoAuthoredBy` setting -> use `attribution` setting instead (has `commit` and `pr` sub-keys, empty string hides)
- `ANTHROPIC_SMALL_FAST_MODEL` env var -> use `ANTHROPIC_DEFAULT_HAIKU_MODEL`
- PreToolUse hook: top-level `decision`/`reason` fields deprecated -> use `hookSpecificOutput.permissionDecision`/`permissionDecisionReason`. Old values `"approve"`/`"block"` map to `"allow"`/`"deny"`
- MCP SSE transport deprecated -> use HTTP transport (`--transport http`)
- MCP scope names changed: `local` (was `project`), `user` (was `global`), `project` (shared `.mcp.json`)
- Plugin `commands/` directory is legacy -> use `skills/` with `SKILL.md` for new plugins

---

## Playbook Maintenance

When docs are updated (detected by `/sync-docs`):
1. Diff the updated pages against previous versions
2. Identify new features, changed syntax, or deprecated patterns
3. Update this playbook to reflect changes
4. Update templates, rules, skills, and agents as needed
5. Record the update date and what changed at the top of this file
