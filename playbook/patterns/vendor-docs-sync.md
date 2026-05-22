# Vendor Docs Sync

## Summary

Pull official documentation from a vendor's online source into the workspace, using manifest-based delta sync. This is for **evolving docs** -- documentation that updates regularly and is already in a machine-readable format. Reserve parsing for static docs that stay valid; evolving docs are mirrored as-is.

## Sync vs Ingest

This is the key decision when adding external documentation to a workspace:

| | Sync | Ingest |
|---|---|---|
| **When** | Docs evolve (weekly/monthly updates) | Docs are static (ships with installer, one version) |
| **Source** | Live website, sitemap, API | PDFs, .docx, offline manuals, ISOs |
| **Format** | Already web-native (markdown, HTML) | Not machine-optimized (scanned PDFs, Word docs) |
| **Processing** | Mirror as-is, no transformation | Parse and restructure into agent-friendly markdown |
| **Storage** | `docs/` or `deps/docs/` (raw mirror) | `docs/` (parsed, one .md per source document) |
| **Delivery** | `scripts/sync-docs.py` (skill wrapper optional) | `/ingest-docs` skill (judgment-heavy) |
| **Re-run** | Regularly (before optimization work, on schedule) | Once per source document (idempotent, re-runnable) |
| **Examples** | Claude Code docs, framework docs, SaaS API docs | Vendor PDFs, instrument manuals, validation docs |

**Rule of thumb:** If the vendor has a docs website with a sitemap or structured URL pattern, sync it. If the vendor ships PDFs with the installer, ingest them. Some products have both -- sync the evolving online docs, ingest the static offline materials.

## When to Use (Sync)

- The workspace depends on software with online documentation that changes
- Docs are already in markdown or clean HTML (machine-readable)
- You need to stay current as the product evolves
- Re-parsing would be wasted effort because the content will change soon

## Source Discovery (in priority order)

When setting up sync for a new product, check for official sources:

1. **Sitemap XML** -- Best case. Structured, includes lastmod timestamps for delta sync. Example: `https://code.claude.com/docs/sitemap.xml`
2. **Docs site with predictable URLs** -- Pages at consistent paths like `/docs/en/<page>.md`. Needs a page listing or index to enumerate.
3. **RSS/Atom feed** -- Release notes or changelogs. Less common for full docs.
4. **API endpoint** -- Products that expose docs via API (OpenAPI specs, etc.).
5. **Version-tagged downloads** -- Docs bundled with releases (GitHub releases, vendor download pages).
6. **No online source** -- Vendor only ships PDFs/docs with installers. This is **ingest** territory, not sync. See the Knowledge Base Repo pattern.

If you cannot find an official online source after checking the vendor's website, support portal, and GitHub/GitLab presence -- **ask the user**. They may know of internal mirrors, have offline copies, or know the vendor's documentation strategy. Confirm with the user before concluding no source exists.

## Implementation

### Manifest-Based Delta Sync

The proven pattern (from CC-Optimizer's `scripts/sync-docs.py`):

```
docs/
  manifest.json    # Tracks per-page lastmod and fetchedAt timestamps
  en/              # Fetched pages (or vendor-specific subdir)
```

Manifest structure:
```json
{
  "source": "https://vendor.com/docs",
  "lastSync": "2026-02-26T12:00:00Z",
  "pages": {
    "page-name": {
      "lastmod": "2026-02-14T01:42:34Z",
      "fetchedAt": "2026-02-26T12:00:00Z"
    }
  }
}
```

### Sync Script Requirements

- Pure Python (no bash/grep/sed dependencies) -- cross-platform
- Uses `urllib` (stdlib) -- no pip dependencies for fetching
- UTF-8 safe (`encoding="utf-8"` everywhere)
- Idempotent and resumable
- Reports summary: total pages, fetched, skipped, failed
- Writes with `newline="\n"` on Windows

### Delivery: script-direct, skill optional

For deterministic doc sync (sitemap-driven, fetch + write), use a plain script — no skill wrapper needed:

```bash
python scripts/sync-docs.py
```

The script does the work. A slash-command skill wrapper is dead weight if the entire skill body is "run this script" — drop it. CC-Optimizer learned this after the original `/sync-docs` skill turned out to wrap a one-line invocation.

When a skill IS worth it: when the sync needs judgment (which sources to pull, when to ingest vs sync, when to skip), wrap in a skill so Claude can branch. For sitemap-driven mirror, the script suffices.

## Where Synced Docs Live

Two placement options depending on workspace type:

- **Code workspace** (project that uses the documented software): `deps/docs/<product>/` -- gitignored, treated as a local dependency cache. Claude references but doesn't commit.
- **Knowledge base workspace** (dedicated to documenting the software): `docs/<product>/` or `docs/en/` -- committed, part of the repo's reference material.

## Rules

- Scrape vendor sites only with the user's knowledge -- the skill should clearly state what URLs it fetches
- Respect robots.txt and rate limits (add delays between fetches if hitting many pages)
- Include User-Agent header identifying the sync tool
- Store the source URL in manifest.json so it's auditable
- Delta sync only -- re-download solely the pages that changed
- Mirror synced docs as-is -- they are already machine-readable and will change, so parsing is wasted effort.

## Real-World Examples

- **CC-Optimizer** -- Syncs the English doc pages from `code.claude.com/docs/sitemap.xml`. Delta sync via lastmod timestamps. Pure Python, stdlib only. Docs change regularly as Claude Code ships features.
- **Lab instrument CDS** -- No online vendor docs (vendor ships PDFs with installers). Uses **ingest**, not sync. All documentation is static and version-pinned.
- **XRD analysis software** -- Pending source discovery. Vendor may have online docs; if not, ingest only.
