#!/usr/bin/env python3
"""Sync Claude Code English documentation from code.claude.com/docs.

Usage: python scripts/sync-docs.py [docs-dir]
docs-dir defaults to ./docs relative to the script's parent project.
"""

import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


USER_AGENT = "CC-Optimizer-Sync/1.0"

# Pages whose URLs serve content also available under another name. The sitemap
# still lists them, but we don't want duplicate cache entries. Verified during
# the 2026-05-07 validation pass.
SKIP_PAGES = frozenset({
    "slash-commands",  # served the /en/skills page after custom commands merged into skills
    "subagents",       # duplicate of /en/sub-agents
})

# URL path prefixes (within /docs/en/) we don't mirror. CC-Optimizer scope is
# Claude Code CLI only; the Agent SDK is documented separately and out of scope.
# Without this filter, /docs/en/agent-sdk/<name> and /docs/en/<name> collapse to
# the same local filename and flip-flop in the cache on each sync.
SKIP_URL_PREFIXES = ("agent-sdk/",)


def fetch_url(url):
    """Fetch a URL with a proper User-Agent header."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def find_project_root():
    """Walk up from script location to find the project root (where docs/ lives)."""
    # Script is at scripts/sync-docs.py — project root is 1 level up.
    return Path(__file__).resolve().parent.parent


def main():
    project_root = find_project_root()
    docs_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else project_root / "docs"
    en_dir = docs_dir / "en"
    manifest_path = docs_dir / "manifest.json"
    sitemap_url = "https://code.claude.com/docs/sitemap.xml"

    en_dir.mkdir(parents=True, exist_ok=True)

    # Load or initialize manifest
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"lastSync": None, "pages": {}}

    # Fetch sitemap
    print("Fetching sitemap...")
    sitemap_xml = fetch_url(sitemap_url).decode("utf-8")

    # Parse sitemap XML
    root = ET.fromstring(sitemap_xml)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    pages = []
    skip_count = 0
    out_of_scope_count = 0
    for url_elem in root.findall("sm:url", ns):
        loc = url_elem.find("sm:loc", ns)
        lastmod = url_elem.find("sm:lastmod", ns)
        if loc is None or lastmod is None:
            continue
        loc_text = loc.text
        # Only English pages
        if loc_text is None or "/docs/en/" not in loc_text:
            continue
        # Path within /docs/en/, used both for prefix-skip and filename derivation.
        relpath = loc_text.split("/docs/en/", 1)[1]
        if any(relpath.startswith(p) for p in SKIP_URL_PREFIXES):
            out_of_scope_count += 1
            continue
        page_name = relpath.rsplit("/", 1)[-1]
        if page_name in SKIP_PAGES:
            skip_count += 1
            continue
        pages.append((page_name, lastmod.text))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total = len(pages)
    fetched = 0
    skipped = 0
    failed = 0
    dead_skipped = 0
    fetched_names = []
    dead_pages = manifest.get("deadPages", {})

    for page_name, lastmod in pages:
        # Skip pages whose .md endpoint 404'd at this lastmod on a prior sync.
        # If sitemap updates the lastmod, we retry in case the page came back.
        if dead_pages.get(page_name) == lastmod:
            dead_skipped += 1
            continue

        existing = manifest.get("pages", {}).get(page_name, {})
        file_path = en_dir / f"{page_name}.md"

        # Skip if already up to date
        if existing.get("lastmod") == lastmod and file_path.exists():
            skipped += 1
            continue

        # Fetch the page
        url = f"https://code.claude.com/docs/en/{page_name}.md"
        try:
            content = fetch_url(url)
            file_path.write_bytes(content)
            fetched += 1
            fetched_names.append(page_name)
            manifest.setdefault("pages", {})[page_name] = {
                "lastmod": lastmod,
                "fetchedAt": now,
            }
            # Page recovered: clear from dead list
            dead_pages.pop(page_name, None)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                dead_pages[page_name] = lastmod
                failed += 1
                print(f"  DEAD: {page_name} (404, will skip on subsequent syncs)")
            else:
                failed += 1
                print(f"  FAILED: {page_name} ({e})")
        except Exception as e:
            failed += 1
            print(f"  FAILED: {page_name} ({e})")

    manifest["deadPages"] = dead_pages

    # Update lastSync
    manifest["lastSync"] = now
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Report
    print()
    print("=== Sync Complete ===")
    print(f"Total pages: {total}")
    print(f"Fetched (new/updated): {fetched}")
    print(f"Skipped (up to date): {skipped}")
    print(f"Skipped (known dead): {dead_skipped}")
    print(f"Skipped (denylisted duplicates): {skip_count}")
    print(f"Skipped (out of scope): {out_of_scope_count}")
    print(f"Failed: {failed}")

    if fetched_names:
        print()
        print("Updated pages:")
        for name in fetched_names:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
