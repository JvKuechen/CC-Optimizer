# Claude Code Plugin Marketplace Reference

> Internal documentation on Claude Code's plugin system and the official demo marketplace.

## Overview

Claude Code has a **plugin system** that extends functionality through reusable packages containing skills, agents, hooks, MCP servers, and LSP servers.

**Two marketplaces exist:**

| Marketplace | ID | Access | Contents |
|-------------|-------|--------|----------|
| Official | `claude-plugins-official` | Auto-available | LSP plugins, external integrations (GitHub, Slack, etc.) |
| Demo | `claude-code-plugins` | Manual add | Example plugins showcasing the system |

## Adding the Demo Marketplace

```bash
/plugin marketplace add anthropics/claude-code
```

Then browse with `/plugin` > **Discover** tab, or install directly:

```bash
/plugin install plugin-name@claude-code-plugins
```

## Demo Marketplace Plugins (13 total)

### Development Tools

| Plugin | Description |
|--------|-------------|
| `frontend-design` | Create distinctive, production-grade UI interfaces avoiding generic AI aesthetics |
| `feature-dev` | 7-phase feature development workflow with exploration, architecture, and review agents |
| `agent-sdk-dev` | Toolkit for Claude Agent SDK development with interactive project setup |
| `plugin-dev` | Toolkit with 7 expert skills for creating Claude Code plugins |
| `claude-opus-4-5-migration` | Migrate code and prompts from Sonnet 4.x / Opus 4.1 to Opus 4.5 |
| `ralph-wiggum` | Self-referential AI loops for iterative development |

### Productivity and Review

| Plugin | Description |
|--------|-------------|
| `code-review` | Automated PR review using multiple specialized agents with confidence scoring |
| `commit-commands` | Git workflow commands for commits, pushes, and PR creation |
| `pr-review-toolkit` | Agents for comments, tests, error handling, and code quality |
| `hookify` | Create custom hooks via markdown files to prevent unwanted behaviors |

### Learning and Output Styles

| Plugin | Description |
|--------|-------------|
| `explanatory-output-style` | Educational insights about implementation choices |
| `learning-output-style` | Interactive mode requesting code contributions at decision points |

### Security

| Plugin | Description |
|--------|-------------|
| `security-guidance` | Hook that warns about injection, XSS, and unsafe code patterns when editing files |

---

## frontend-design Plugin Deep Dive

**Authors:** Prithvi Rajasekaran, Alexander Bricken (Anthropic)
**Version:** 1.0.0
**Type:** Agent Skill (auto-invoked when Claude detects frontend tasks)

### What It Does

Guides Claude to create distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. It's a **skill** (not a slash command), meaning Claude automatically applies it when detecting frontend/UI work.

### Design Framework

The skill uses a four-part design thinking approach:

1. **Purpose** - Problem-solving intent and user context
2. **Tone** - Choose an extreme aesthetic direction (minimalist, maximalist, retro, organic, luxury, playful, etc.)
3. **Constraints** - Technical framework and performance requirements
4. **Differentiation** - The singular memorable element

**Key principle:** "Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity."

### Aesthetic Guidelines

**Typography:**
- Prioritize distinctive, characterful fonts
- Avoid generic fonts like Arial and Inter
- Pair display and body fonts intentionally

**Color & Theme:**
- "Dominant colors with sharp accents outperform timid, evenly-distributed palettes"

**Motion:**
- High-impact moments like staggered page load reveals
- Scroll-triggered animations and hover states

**Spatial Composition:**
- Asymmetry, overlap, diagonal flow
- Grid-breaking elements

**Backgrounds & Visual Details:**
- Gradients, textures, patterns
- Layered atmospheric effects

### Anti-Patterns (Explicitly Forbidden)

The skill instructs Claude to NEVER use:
- Overused fonts (Arial, generic sans-serif)
- Cliched purple gradients
- Predictable layouts
- Cookie-cutter design lacking context-specific character

### Example Use Cases

From the README:
- Music streaming app dashboards
- Landing pages for tech startups (e.g., AI security companies)
- Settings panels with dark mode functionality

### Installation

```bash
/plugin marketplace add anthropics/claude-code
/plugin install frontend-design@claude-code-plugins
```

After installation, the skill auto-activates when Claude detects frontend work. No slash command needed.

---

## Official Marketplace: Code Intelligence Plugins

The built-in `claude-plugins-official` marketplace includes LSP plugins for real-time code intelligence:

| Language | Plugin | Binary Required |
|----------|--------|-----------------|
| TypeScript | `typescript-lsp` | `typescript-language-server` |
| Python | `pyright-lsp` | `pyright-langserver` |
| Rust | `rust-analyzer-lsp` | `rust-analyzer` |
| Go | `gopls-lsp` | `gopls` |
| C/C++ | `clangd-lsp` | `clangd` |
| Java | `jdtls-lsp` | `jdtls` |
| PHP | `php-lsp` | `intelephense` |
| Swift | `swift-lsp` | `sourcekit-lsp` |
| Kotlin | `kotlin-lsp` | `kotlin-language-server` |
| Lua | `lua-lsp` | `lua-language-server` |
| C# | `csharp-lsp` | `csharp-ls` |

**What LSP provides:**
- Automatic diagnostics after every edit (type errors, missing imports)
- Code navigation (jump to definition, find references, hover info)

## Official Marketplace: External Integrations

Pre-configured MCP server plugins:

| Category | Plugins |
|----------|---------|
| Source Control | `github`, `gitlab` |
| Project Management | `atlassian` (Jira/Confluence), `asana`, `linear`, `notion` |
| Design | `figma` |
| Infrastructure | `vercel`, `firebase`, `supabase` |
| Communication | `slack` |
| Monitoring | `sentry` |

---

## Plugin Installation Scopes

When installing via the `/plugin` UI, choose a scope:

| Scope | Stored In | Shared With |
|-------|-----------|-------------|
| User | `~/.claude/settings.json` | Just you, all projects |
| Project | `.claude/settings.json` | All collaborators on this repo |
| Local | `.claude/settings.local.json` | Just you, this repo only |
| Managed | Admin-controlled | Organization-wide |

---

## CLI Reference

```bash
# Add marketplace
/plugin marketplace add anthropics/claude-code
/plugin marketplace add https://gitlab.com/company/plugins.git
/plugin marketplace add ./local-path

# List marketplaces
/plugin marketplace list

# Update marketplace
/plugin marketplace update marketplace-name

# Remove marketplace
/plugin marketplace remove marketplace-name

# Install plugin
/plugin install plugin-name@marketplace-name
/plugin install plugin-name@marketplace-name --scope project

# Manage plugins
/plugin disable plugin-name@marketplace-name
/plugin enable plugin-name@marketplace-name
/plugin uninstall plugin-name@marketplace-name

# Interactive UI
/plugin
```

---

## Creating Custom Plugins

See `docs/en/plugins.md` for full authoring guide. Key structure:

```
my-plugin/
  .claude-plugin/
    plugin.json       # Manifest (required)
  commands/           # Slash commands
  skills/             # Agent skills (auto-invoked)
  agents/             # Custom agents
  hooks/
    hooks.json        # Event handlers
  .mcp.json           # MCP server configs
  .lsp.json           # LSP server configs
```

Test locally with:
```bash
claude --plugin-dir ./my-plugin
```

---

## References

- Plugin authoring: `docs/en/plugins.md`
- Plugin discovery: `docs/en/discover-plugins.md`
- Marketplace creation: `docs/en/plugin-marketplaces.md`
- Technical reference: `docs/en/plugins-reference.md`
- Demo marketplace source: https://github.com/anthropics/claude-code/tree/main/plugins
