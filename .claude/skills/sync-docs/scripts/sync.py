#!/usr/bin/env python3
"""Sync Claude Code English documentation from code.claude.com/docs.

Usage: python sync.py [docs-dir]
docs-dir defaults to ./docs relative to the script's parent project.
"""

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


USER_AGENT = "CC-Optimizer-Sync/1.0"


def fetch_url(url):
    """Fetch a URL with a proper User-Agent header."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def find_project_root():
    """Walk up from script location to find the project root (where docs/ lives)."""
    script_dir = Path(__file__).resolve().parent
    # Script is at .claude/skills/sync-docs/scripts/sync.py
    # Project root is 4 levels up
    return script_dir.parent.parent.parent.parent


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
    for url_elem in root.findall("sm:url", ns):
        loc = url_elem.find("sm:loc", ns)
        lastmod = url_elem.find("sm:lastmod", ns)
        if loc is None or lastmod is None:
            continue
        loc_text = loc.text
        # Only English pages
        if "/docs/en/" not in loc_text:
            continue
        page_name = loc_text.rsplit("/", 1)[-1]
        pages.append((page_name, lastmod.text))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total = len(pages)
    fetched = 0
    skipped = 0
    failed = 0
    fetched_names = []

    for page_name, lastmod in pages:
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
        except Exception as e:
            failed += 1
            print(f"  FAILED: {page_name} ({e})")

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
    print(f"Failed: {failed}")

    if fetched_names:
        print()
        print("Updated pages:")
        for name in fetched_names:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
