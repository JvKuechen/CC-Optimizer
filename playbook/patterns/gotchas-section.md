# Gotchas Section

**Source:** Discovered across multiple workspace audits

## When

Any project where you've hit non-obvious platform behavior, API quirks, or bugs that cost debugging time. Prevents Claude (and future you) from repeating mistakes.

## How

Add a `## Gotchas` section to CLAUDE.md with terse entries. Each gotcha states the trap and the fix.

```markdown
## Gotchas

- Graph API returns 403 on `/onlineMeetings` if app-only auth is used -- requires delegated permissions
- Power Automate custom connectors silently drop query params with dots in names
- `bool("False")` is `True` in Python but `false` in Lua -- UE4SS config files use Lua semantics
- SAM format (`DOMAIN\user`) fails on LDAPS; use UPN format (`user@domain.com`) instead
- Python MCP servers fail on Windows with `"command": "python"` -- Node.js spawn can't resolve Windows Store alias. Use `"command": "cmd", "args": ["/c", "python", "-m", "pkg"]`
```

## Rules

- One line per gotcha, no paragraphs
- State the mistake AND the fix (not just "watch out for X")
- Add new gotchas as they're discovered, don't wait for a cleanup pass
- If a gotcha has a code fix, put the fix inline or link to the commit
