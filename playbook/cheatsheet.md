# Claude Code Cheat Sheet

Features beyond the basics. Excludes features we already use daily
(--init, Ctrl+O, --resume/--continue, /compact, /clear, Esc+Esc, Ctrl+B).

---

## Global Features (set up once, works everywhere)

### Plugins & Marketplace

Browse and install plugins that add skills, hooks, tools, and integrations.
Installed at user scope = available in all projects.

```
/plugin                          # Open plugin manager UI
/plugin install <name>           # Install a plugin
/plugin uninstall <name>         # Remove a plugin
/plugin enable / disable <name>  # Toggle without removing
/plugin marketplace update       # Refresh marketplace listings
```

Recommended global plugins:
- **LSP plugin for your primary language** (pyright-lsp, typescript-lsp, etc.)
  Gives Claude jump-to-definition, find-references, auto-diagnostics after edits.
- **commit-commands** — Git commit workflow shortcuts
- **pr-review-toolkit** — PR review agents

### Chrome Integration

Claude controls a real Chrome browser — navigate, click, type, read console,
take screenshots, record GIFs. Useful for testing UI or scraping authenticated apps.

```
claude --chrome                  # Start session with Chrome enabled
/chrome                          # Enable/manage mid-session
```

To enable by default, add to settings:
```json
{ "preferences": { "chrome": true } }
```

### Extended Thinking (Alt+T)

Toggle deeper reasoning mode. Uses more tokens but better for architectural
decisions, complex debugging, and multi-step analysis. Toggle per-session.

```
Alt+T  or  Option+T             # Toggle thinking on/off
```

### Output Styles

Change Claude's communication style. Persists per session.

```
/output-style                    # Pick from available styles
/output-style explanatory        # Educational insights while coding
/output-style learning           # Interactive with TODO markers
```

Custom styles can be created as plugins or files.

### Headless Mode (claude -p)

Run Claude non-interactively. Essential for scripts, CI, and batch operations.

```bash
claude -p "Explain this project"                      # One-shot query
claude -p "List endpoints" --output-format json        # JSON output
claude -p "Analyze log" --output-format stream-json    # Streaming JSON
claude -p "Migrate file" --allowedTools "Edit,Read"    # Scoped tools
claude -p "Review code" --max-turns 5                  # Limit iterations
cat file.txt | claude -p "Summarize this"              # Pipe input
```

### Desktop App

Separate install. Adds: diff view with line comments, git worktrees for
parallel sessions, remote session launch, custom environment variables.

### General Commands

```
/context                         # Visualize context usage (colored grid)
/export [filename]               # Save conversation to file or clipboard
/rename <name>                   # Name session for easy resume later
/doctor                          # Health check installation
! <command>                      # Run bash directly without Claude
@ <path>                         # Reference file in prompt (autocomplete)
```

---

## Per-Project Features (set up in each workspace)

These require project-specific configuration. Include decisions about these
in Phase 1 of the optimization checklist.

### MCP Servers

Connect Claude to external services: databases, APIs, issue trackers.
Configured per-project in `.mcp.json` at project root.

```bash
claude mcp add <name> <command>                 # Add stdio server
claude mcp add <name> --url <url>               # Add HTTP server
claude mcp add-json <name> '{"command":...}'    # Add from JSON
claude mcp list                                 # List configured servers
claude mcp remove <name>                        # Remove a server
```

Example `.mcp.json`:
```json
{
  "mcpServers": {
    "database": {
      "command": "npx",
      "args": ["@anthropic/mcp-server-sqlite", "path/to/db.sqlite"]
    }
  }
}
```

Potential per-project MCP servers:
- SQL Server / SQLite / Postgres database
- GitHub (if project uses GitHub)
- Jira / Linear / Asana (issue tracking)
- Sentry (error monitoring)
- File system (restricted access to specific dirs)

### LSP Plugins (language-specific)

While plugins install globally, LSP servers activate per-project based on
the language. Install the right one for each project's stack:

| Language   | Plugin            |
|------------|-------------------|
| Python     | pyright-lsp       |
| TypeScript | typescript-lsp    |
| C#         | csharp-lsp        |
| Go         | gopls-lsp         |
| Rust       | rust-analyzer-lsp |
| Java       | jdtls-lsp         |
| C/C++      | clangd-lsp        |
| PHP        | php-lsp           |
| Kotlin     | kotlin-lsp        |
| Swift      | swift-lsp         |
| Lua        | lua-lsp           |

### Multi-Directory Access (--add-dir)

Work across multiple codebases in one session. Use this when optimizing
a target workspace from the optimizer workspace:

```bash
claude --add-dir C:\path\to\target\workspace
```

### Sandboxing

OS-level filesystem and network isolation. Configure per-project for
sensitive workspaces.

```
/sandbox                         # Enable and configure
```

Settings: allowedPaths, deniedPaths, network domain filtering.
Note: Limited on Windows (Seatbelt = macOS, bubblewrap = Linux).

### Fan-Out Pattern

Batch process many files in parallel using headless mode:

```bash
for file in $(cat files.txt); do
  claude -p "Migrate $file from X to Y" --allowedTools "Edit,Read" &
done
wait
```

Useful for: migrations, bulk refactoring, generating docs per module.

---

## Keyboard Shortcuts Reference

| Shortcut       | Action                                    |
|----------------|-------------------------------------------|
| Ctrl+G         | Open prompt/plan in text editor           |
| Shift+Tab      | Cycle permission modes (normal/plan/auto) |
| Alt+T          | Toggle extended thinking                  |
| Alt+P          | Switch model (opus/sonnet/haiku)          |
| Ctrl+T         | Toggle task list view                     |
| Ctrl+L         | Clear terminal (keeps conversation)       |
| Ctrl+R         | Search command history                    |
| Ctrl+V         | Paste image from clipboard                |
| Esc+Esc        | Rewind checkpoint menu                    |
| Ctrl+B         | Background running task                   |
| Ctrl+O         | Toggle verbose output                     |
| \ + Enter      | Multiline input                           |
