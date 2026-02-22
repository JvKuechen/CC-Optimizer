---
name: sync-docs
description: Sync local copy of Claude Code documentation from code.claude.com/docs
disable-model-invocation: true
allowed-tools: Bash
---

Sync the local documentation mirror by running the sync script:

```bash
python .claude/skills/sync-docs/scripts/sync.py
```

The script (Python, cross-platform — no bash/grep/mapfile dependencies):
1. Fetches the sitemap XML from `https://code.claude.com/docs/sitemap.xml`
2. Parses it with `xml.etree.ElementTree` to extract English page names and `<lastmod>` timestamps
3. Compares against `docs/manifest.json` — only fetches pages that are new or have a newer `lastmod`
4. Downloads updated pages via `urllib` to `docs/en/<page>.md`
5. Updates the manifest with new timestamps
6. Prints a summary of what changed

Report the script's output to the user. If any pages failed, note them.
