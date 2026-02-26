# Knowledge Base Repo

## Summary

A "read, document, but don't touch" repository for external software that the team uses but does not develop. Claude reads vendor docs, helpdesk tickets, and configuration exports to answer questions and maintain a wiki -- but never modifies the software itself.

These repos deal primarily with **static documentation** -- vendor manuals, PDFs, installer guides that ship once per version and don't change. Unlike evolving online docs (which you sync as-is), static docs need to be **ingested** and restructured into agent-friendly markdown because they aren't optimized for machine consumption.

## When to Use

- Commercial or third-party software the team uses but doesn't develop (lab instruments, ERP, LIMS, CDS, etc.)
- The team needs a single place to search troubleshooting history, vendor docs, and internal knowledge
- Source materials are primarily static (PDFs, .docx, offline manuals, installer media)
- Helpdesk or chatbot integration is planned
- Multiple source materials exist that may contradict each other

## Sync vs Ingest

See `patterns/vendor-docs-sync.md` for the full decision framework. The short version:

- **Evolving docs** (online, machine-readable, changes regularly) = **sync** as-is. Don't parse what will change next week.
- **Static docs** (PDFs, .docx, ships with installer) = **ingest** into agent-optimized markdown. Worth the parsing effort because the content is stable and the raw format is not machine-friendly.

Most knowledge base repos are ingest-heavy. Some products have both -- sync the online release notes, ingest the offline manuals.

## Structure

```
project/
  CLAUDE.md             # Q&A-optimized guide with search order and contradiction policy
  README.md             # Quick start for cloning and using
  .claude/
    settings.json       # Permissions for git, python, curl, file ops
    rules/              # context-handoff.md, windows-shell.md
    skills/
      ingest-docs/      # Parse Import/ -> docs/ (static materials)
      search-helpdesk/  # Query helpdesk API for tickets/articles
      update-wiki/      # Build wiki from verified docs
      sync-vendor-docs/ # Pull from official online sources (if available)
  docs/                 # Agent-optimized markdown from all sources
    contradictions.md   # Cross-source conflicts awaiting user resolution
    index.md            # Master cross-reference
  config/               # Exported software configurations
  wiki/                 # Nested parallel checkout (Gitea wiki, separate .git)
  scripts/
    setup.py            # Post-clone: clone wiki, install pre-push hook
  playbook/
    roadmap.md          # Phased project plan
  Import/               # LOCAL ONLY (gitignored). Raw materials: installers, PDFs, manuals
  .gitignore            # Import/, wiki/, .venv/, .env, settings.local.json
  .gitattributes        # * text=auto eol=lf
```

## Three-Layer Knowledge Pipeline

1. **Import/** (raw, local-only) -- User drops installers, manuals, ticket exports, configs. Never committed. This is the messy input.
2. **docs/** (parsed, committed) -- Agent-optimized markdown extracted from Import/ by `/ingest-docs`. One file per source document. Structured for Claude to search and reference. Worth the effort because these docs are static -- they ship with the installer and won't change until the next major version.
3. **wiki/** (verified, separate repo) -- Human-reviewed knowledge base built from docs/ by `/update-wiki`. This is what techs and chatbots consume. Source of truth.

## Why Ingest Static Docs

Raw vendor materials are hostile to agents:
- Scanned PDFs with no text layer (need OCR)
- Word docs with complex formatting that loses structure in extraction
- Manuals with tables that don't survive copy-paste
- Cross-references that are page numbers, not links
- Headers buried in formatting rather than semantic structure

Ingestion restructures this into clean markdown with:
- Proper heading hierarchy
- Menu paths in consistent format (`Menu > Submenu > Option`)
- Tables preserved as markdown tables
- Source document and page noted at top of each file
- One file per source document (searchable, diffable)

This investment pays off because the content is stable. A vendor manual for version X.Y won't change -- but Claude will reference it hundreds of times.

## Contradiction Resolution

Sources will conflict. The workflow:

1. During ingestion, `/ingest-docs` builds `docs/contradictions.md` listing each conflict with quoted sources and file paths.
2. `/update-wiki` refuses to write a wiki page that has unresolved contradictions.
3. The user reviews contradictions and confirms which source is correct.
4. The resolution is recorded in `docs/contradictions.md` and noted in the wiki page.

Common contradiction patterns:
- Version-specific procedures that changed between releases
- Vendor manual describes defaults vs our custom configuration
- Helpdesk workaround contradicts official procedure
- Installer README conflicts with user manual

## CLAUDE.md Shape

The CLAUDE.md for a knowledge base repo is different from a code repo:

- **No build/test/lint commands** -- there's no code to build
- **Search order** is critical: helpdesk -> wiki -> docs -> config
- **Contradiction policy** section tells Claude to flag conflicts, not silently pick one
- **Domain context** section describes the software, instruments, deployment
- **Vendor support** section with contact info and case-opening tips
- **Source materials** section lists what's in Import/

## Skills

| Skill | Purpose | Key behavior |
|-------|---------|------------|
| `/ingest-docs` | Parse Import/ -> docs/ | Restructures static docs into agent-friendly markdown. Tracks contradictions. One md per source |
| `/search-helpdesk` | Query helpdesk API | Score thresholds, multiple search terms |
| `/update-wiki` | Build wiki from docs/ | Blocks on unresolved contradictions |
| `/sync-vendor-docs` | Pull evolving online docs | Optional -- only if vendor has a docs site with changing content |

## Rules

- Import/ is always gitignored (large files, installers, ISOs)
- Wiki uses `master` branch (Gitea/GitHub wiki requirement)
- Never auto-push wiki changes -- human review required
- Configuration exports in config/ are committed (small, useful for reference)
- Python venv for ingestion tools (.venv/, gitignored)

## Related Patterns

- **Vendor Docs Sync** -- for the evolving-docs side of the equation
- **Nested Parallel Checkout** -- wiki/ as a separate git repo
- **Gitignored Search Reminder** -- hook to remind about wiki/ and Import/ in grep searches

## Real-World Examples

- **Chromatography CDS** -- Vendor-shipped enterprise docs (.docx), scanned validation PDFs (OCR'd), support case exports (HTML), and hardware manuals ingested into agent-optimized markdown. 18 wiki pages covering installation, troubleshooting, SQL schema, instrument configuration. No online docs to sync -- everything is static.
- **XRD Analysis Software** -- Same structure with contradiction resolution baked into skills from the start. Multiple source types (manuals, installers, helpdesk tickets) expected to conflict on version-specific procedures.
