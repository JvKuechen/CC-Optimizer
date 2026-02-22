"""Seed portfolio wiki with project documentation.

Copies WIKI.md and raw-analysis.md files from claudes/ projects
to the portfolio docs/projects/ directory.

No LLM needed - just deterministic file copying with light formatting.
"""
import re
from pathlib import Path
from datetime import datetime
from config import load_user_config, load_projects_config, resolve_claudes_dir

# --- Config-driven paths and settings ---
_user_config = load_user_config()
_projects_config = load_projects_config()

CLAUDES_DIR = resolve_claudes_dir(_user_config)

# Portfolio docs dir: relative to claudes_dir, configurable via user config
_portfolio_rel = _user_config.get(
    "portfolio_docs_dir", "Personal/portfolio/docs/projects"
)
PORTFOLIO_DOCS = CLAUDES_DIR / _portfolio_rel

# Projects to skip (not portfolio material)
SKIP_PROJECTS = set(_projects_config.get("portfolio_skip", []))

# Prefer these files in order (not personal data, stays hardcoded)
DOC_PRIORITY = ["WIKI.md", "raw-analysis.md", "README.md", "CLAUDE.md"]


def find_best_doc(project_dir: Path) -> Path | None:
    """Find the best documentation file for a project."""
    for doc_name in DOC_PRIORITY:
        doc_path = project_dir / doc_name
        if doc_path.exists() and doc_path.stat().st_size > 200:  # Skip tiny placeholders
            return doc_path
    return None


def extract_title(content: str, fallback: str) -> str:
    """Extract title from markdown content."""
    # Look for # Title at start
    match = re.match(r'^#\s+(.+)$', content.strip(), re.MULTILINE)
    if match:
        return match.group(1).strip()
    return fallback.replace("-", " ").replace("_", " ").title()


def clean_content(content: str, project_name: str) -> str:
    """Clean up content for portfolio display."""
    lines = content.split('\n')
    cleaned = []

    for line in lines:
        # Skip lines that are just placeholders
        if line.strip().startswith('[') and 'see above' in line.lower():
            continue
        if line.strip().startswith('[') and 'content as shown' in line.lower():
            continue
        cleaned.append(line)

    return '\n'.join(cleaned)


def categorize_project(project_path: Path) -> str:
    """Determine if project is Work or Personal."""
    if "Work" in str(project_path):
        return "work"
    return "personal"


def generate_portfolio_page(project_dir: Path) -> str | None:
    """Generate a portfolio page from project documentation."""
    doc_path = find_best_doc(project_dir)
    if not doc_path:
        return None

    content = doc_path.read_text(encoding='utf-8', errors='replace')

    # Skip if content is too short or just a placeholder
    if len(content) < 200:
        return None
    if 'see above' in content.lower() and len(content) < 500:
        return None

    project_name = project_dir.name
    title = extract_title(content, project_name)
    category = categorize_project(project_dir)
    cleaned = clean_content(content, project_name)

    # Add portfolio metadata header
    header = f"""<!--
  Portfolio page for: {project_name}
  Category: {category}
  Source: {doc_path.name}
  Generated: {datetime.now().strftime('%Y-%m-%d')}

  This page was auto-generated from project documentation.
  For updates, edit the source file or regenerate.
-->

"""

    return header + cleaned


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Seed portfolio with project docs")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--category", choices=["work", "personal", "all"], default="personal",
                        help="Which category to process (default: personal)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    # Ensure output directory exists
    PORTFOLIO_DOCS.mkdir(parents=True, exist_ok=True)

    # Collect projects
    categories = ["Personal"] if args.category == "personal" else \
                 ["Work"] if args.category == "work" else \
                 ["Work", "Personal"]

    projects = []
    for category in categories:
        category_dir = CLAUDES_DIR / category
        if not category_dir.exists():
            continue
        for project_dir in sorted(category_dir.iterdir()):
            if not project_dir.is_dir():
                continue
            if project_dir.name.startswith('.'):
                continue
            if project_dir.name in SKIP_PROJECTS:
                continue
            projects.append(project_dir)

    print(f"Found {len(projects)} projects to process")

    stats = {"created": 0, "skipped_exists": 0, "skipped_no_doc": 0, "skipped_placeholder": 0}

    for project_dir in projects:
        project_name = project_dir.name
        output_path = PORTFOLIO_DOCS / f"{project_name}.md"

        # Check if already exists
        if output_path.exists() and not args.force:
            print(f"  [SKIP] {project_name} - already exists")
            stats["skipped_exists"] += 1
            continue

        # Generate content
        content = generate_portfolio_page(project_dir)

        if content is None:
            doc = find_best_doc(project_dir)
            if doc is None:
                print(f"  [SKIP] {project_name} - no documentation found")
                stats["skipped_no_doc"] += 1
            else:
                print(f"  [SKIP] {project_name} - placeholder content only")
                stats["skipped_placeholder"] += 1
            continue

        if args.dry_run:
            print(f"  [WOULD CREATE] {project_name} -> {output_path.name}")
        else:
            output_path.write_text(content, encoding='utf-8')
            print(f"  [CREATED] {project_name} -> {output_path.name} ({len(content)} bytes)")

        stats["created"] += 1

    print(f"\n=== Summary ===")
    print(f"Created: {stats['created']}")
    print(f"Skipped (exists): {stats['skipped_exists']}")
    print(f"Skipped (no docs): {stats['skipped_no_doc']}")
    print(f"Skipped (placeholder): {stats['skipped_placeholder']}")

    if not args.dry_run and stats['created'] > 0:
        # Update sidebar
        update_sidebar()


def update_sidebar():
    """Update the Docsify sidebar with project links."""
    sidebar_path = PORTFOLIO_DOCS.parent / "_sidebar.md"

    # Get all project pages
    project_files = sorted(PORTFOLIO_DOCS.glob("*.md"))

    if not project_files:
        return

    # Read existing sidebar
    if sidebar_path.exists():
        existing = sidebar_path.read_text(encoding='utf-8')
    else:
        existing = ""

    # Build project links section
    project_links = "\n* **Projects**\n"
    for pf in project_files:
        name = pf.stem.replace("-", " ").replace("_", " ").title()
        project_links += f"  * [{name}](projects/{pf.name})\n"

    # Check if projects section exists
    if "* **Projects**" in existing:
        # Replace existing projects section
        pattern = r'\* \*\*Projects\*\*\n(?:  \* \[.*?\]\(projects/.*?\)\n)*'
        updated = re.sub(pattern, project_links, existing)
    else:
        # Append projects section
        updated = existing.rstrip() + "\n" + project_links

    sidebar_path.write_text(updated, encoding='utf-8')
    print(f"\nUpdated sidebar with {len(project_files)} project links")


if __name__ == "__main__":
    main()
