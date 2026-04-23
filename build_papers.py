#!/usr/bin/env python3
"""
build_papers.py — Generate per-paper static HTML pages from data/publications.json.

For every paper in publications.json that has a `pageUrl` set, this script writes
an HTML file at that path with:
  - Google Scholar <meta name="citation_*"> tags for indexing
  - Open Graph tags for nice link previews (LinkedIn, Slack, Twitter, ...)
  - <link rel="canonical"> for SEO
  - The same visual layout as the existing hand-written paper pages

No external dependencies — only the Python standard library.

Usage (from the repo root):
    python3 build_papers.py

Options:
    --check    Exit non-zero if any page would change (for CI).
    --quiet    Suppress per-file output, print only summary.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DATA_FILE = REPO_ROOT / "data" / "publications.json"


def esc(value) -> str:
    """HTML-escape a value; None -> empty string. For text nodes AND attributes."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def meta_tag(name: str, content) -> str:
    """Render a <meta name="..." content="..."> line, or empty string if no content."""
    if content is None or content == "":
        return ""
    return f'    <meta name="{esc(name)}" content="{esc(content)}" />'


def og_tag(prop: str, content) -> str:
    if content is None or content == "":
        return ""
    return f'    <meta property="{esc(prop)}" content="{esc(content)}" />'


def rel_depth(page_url: str) -> str:
    """Return a relative prefix like '../../' based on how deep pageUrl is."""
    # pageUrl is like "papers/iatl/iatl.html" -> 2 parent dirs up
    depth = page_url.count("/")
    return "../" * depth


def render_citation_authors(authors: list[str]) -> str:
    lines = []
    for author in authors or []:
        lines.append(meta_tag("citation_author", author))
    return "\n".join(line for line in lines if line)


def render_authors_inline(authors: list[str]) -> str:
    return ", ".join(esc(a) for a in (authors or []))


def render_meta_line(paper: dict) -> str:
    """Build the 'Venue • Location • Pages • Date' line."""
    parts = []
    if paper.get("venueShort"):
        parts.append(esc(paper["venueShort"]))
    if paper.get("location"):
        parts.append(esc(paper["location"]))
    if paper.get("pages"):
        parts.append(f"pp. {esc(paper['pages'])}")
    if paper.get("publicationDate"):
        parts.append(esc(paper["publicationDate"]))
    return " • ".join(parts)


def render_paper_actions(paper: dict) -> str:
    """PDF download + Official page buttons."""
    bits = []
    pdf_filename = paper.get("pdfFilename")
    if pdf_filename:
        bits.append(
            f'            <a class="btn-primary" href="{esc(pdf_filename)}">\n'
            f'                <i class="fa-solid fa-file-pdf"></i> Download PDF\n'
            f'            </a>'
        )
    official = paper.get("officialUrl")
    if official:
        label = paper.get("officialLabel") or "Official page"
        bits.append(
            f'            <a class="btn-outline" href="{esc(official)}" target="_blank" rel="noopener noreferrer">\n'
            f'                <i class="fa-solid fa-arrow-up-right-from-square"></i> {esc(label)}\n'
            f'            </a>'
        )
    return "\n".join(bits)


def render_paper_top(paper: dict, back_href: str) -> str:
    badge = paper.get("badge")
    badge_html = f'<span class="paper-badge">{esc(badge)}</span>' if badge else ""
    return (
        '        <div class="paper-top">\n'
        f'            <a class="paper-back" href="{esc(back_href)}">← Back to home</a>\n'
        f'            {badge_html}\n'
        '        </div>'
    )


def render_bibtex_section(paper: dict) -> str:
    bibtex = paper.get("bibtex") or "TBA"
    return (
        '        <section class="paper-section">\n'
        '            <h2>BibTeX</h2>\n'
        f'<pre class="pub-bibtex">{esc(bibtex)}</pre>\n'
        '        </section>'
    )


def build_page(paper: dict, base_url: str) -> str:
    """Return the full HTML string for a single paper page."""
    page_url = paper["pageUrl"]  # e.g. "papers/iatl/iatl.html"
    rel = rel_depth(page_url)  # "../../"

    canonical_url = f"{base_url.rstrip('/')}/{page_url}"
    pdf_abs_url = (
        f"{base_url.rstrip('/')}/{page_url.rsplit('/', 1)[0]}/{paper['pdfFilename']}"
        if paper.get("pdfFilename")
        else None
    )

    # Scholar-style meta tags
    scholar_meta = []
    scholar_meta.append(meta_tag("citation_title", paper.get("title")))
    scholar_meta.append(render_citation_authors(paper.get("authors", [])))
    if paper.get("conferenceTitle"):
        scholar_meta.append(meta_tag("citation_conference_title", paper["conferenceTitle"]))
    if paper.get("journalTitle"):
        scholar_meta.append(meta_tag("citation_journal_title", paper["journalTitle"]))
    if paper.get("year") and paper.get("month"):
        scholar_meta.append(meta_tag("citation_publication_date", f"{paper['year']}/{paper['month']}"))
    elif paper.get("year"):
        scholar_meta.append(meta_tag("citation_publication_date", paper["year"]))
    scholar_meta.append(meta_tag("citation_firstpage", paper.get("firstPage")))
    scholar_meta.append(meta_tag("citation_lastpage", paper.get("lastPage")))
    scholar_meta.append(meta_tag("citation_doi", paper.get("doi")))
    scholar_meta.append(meta_tag("citation_pdf_url", pdf_abs_url))
    scholar_meta.append(meta_tag("citation_abstract_html_url", canonical_url))
    scholar_meta.append(meta_tag("citation_language", "en"))
    scholar_meta_block = "\n".join(line for line in scholar_meta if line)

    # Open Graph + Twitter
    og_description = (paper.get("abstract") or "")[:300].replace("\n", " ").strip()
    if len(paper.get("abstract") or "") > 300:
        og_description = og_description.rstrip() + "…"
    og_meta = "\n".join(
        line
        for line in [
            og_tag("og:type", "article"),
            og_tag("og:title", paper.get("title")),
            og_tag("og:description", og_description),
            og_tag("og:url", canonical_url),
            og_tag("og:site_name", "Andrea Capone"),
            meta_tag("twitter:card", "summary"),
            meta_tag("twitter:title", paper.get("title")),
            meta_tag("twitter:description", og_description),
        ]
        if line
    )

    # SEO description (short abstract)
    description = og_description

    # Body
    authors_line = render_authors_inline(paper.get("authors", []))
    meta_line = render_meta_line(paper)
    paper_top = render_paper_top(paper, back_href=f"{rel}index.html")
    paper_actions = render_paper_actions(paper)
    bibtex_section = render_bibtex_section(paper)

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{esc(paper.get('title'))} — Andrea Capone</title>
    <meta name="description" content="{esc(description)}" />
    <link rel="canonical" href="{esc(canonical_url)}" />

    <!-- Google Scholar / Highwire Press -->
{scholar_meta_block}

    <!-- Open Graph / Twitter -->
{og_meta}

    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
    <link rel="stylesheet" href="{rel}styles.css" />
</head>

<body>
<main class="section">
    <div class="section-container paper-container">

{paper_top}

        <h1 class="paper-title">{esc(paper.get('title'))}</h1>

        <p class="paper-authors">
            {authors_line}
        </p>

        <p class="paper-meta">
            {meta_line}
        </p>

        <div class="paper-actions">
{paper_actions}
        </div>

        <hr class="about-separator" />

        <section class="paper-section">
            <h2>Abstract</h2>
            <p>{esc(paper.get('abstract') or '')}</p>
        </section>

{bibtex_section}

    </div>
</main>
</body>
</html>
"""


def load_data() -> dict:
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_paper(paper: dict) -> list[str]:
    """Return a list of validation errors for a single paper (empty if all good)."""
    errors = []
    required = ["id", "title", "year", "abstract"]
    for field in required:
        if not paper.get(field):
            errors.append(f"missing required field '{field}'")
    if paper.get("pageUrl"):
        # If we're going to generate a page, we need authors and a PDF filename
        if not paper.get("authors"):
            errors.append("pageUrl is set but 'authors' is missing or empty")
        if not paper.get("pdfFilename"):
            errors.append("pageUrl is set but 'pdfFilename' is missing (needed for Scholar citation_pdf_url)")
    return errors


def build_all(*, check_only: bool = False, quiet: bool = False) -> int:
    """Build every paper page. Returns exit code."""
    data = load_data()
    base_url = data.get("baseUrl", "").rstrip("/")
    if not base_url:
        print("ERROR: 'baseUrl' is missing from publications.json", file=sys.stderr)
        return 2

    all_papers = data.get("papers", []) + data.get("theses", [])
    papers_with_pages = [p for p in all_papers if p.get("pageUrl")]

    # Validate first
    had_validation_errors = False
    for paper in papers_with_pages:
        errors = validate_paper(paper)
        if errors:
            had_validation_errors = True
            for err in errors:
                print(f"ERROR [{paper.get('id', '?')}]: {err}", file=sys.stderr)
    if had_validation_errors:
        return 2

    changed = []
    unchanged = []
    created = []

    for paper in papers_with_pages:
        page_path = REPO_ROOT / paper["pageUrl"]
        new_content = build_page(paper, base_url)

        if page_path.exists():
            old_content = page_path.read_text(encoding="utf-8")
            if old_content == new_content:
                unchanged.append(paper["pageUrl"])
                if not quiet:
                    print(f"  unchanged: {paper['pageUrl']}")
                continue
            else:
                changed.append(paper["pageUrl"])
                if not quiet:
                    print(f"  updated:   {paper['pageUrl']}")
        else:
            created.append(paper["pageUrl"])
            if not quiet:
                print(f"  created:   {paper['pageUrl']}")

        if not check_only:
            page_path.parent.mkdir(parents=True, exist_ok=True)
            page_path.write_text(new_content, encoding="utf-8")

    # Summary
    total = len(papers_with_pages)
    print(
        f"\n{total} page(s) processed — "
        f"{len(created)} created, {len(changed)} updated, {len(unchanged)} unchanged."
    )

    if check_only and (created or changed):
        print(
            "\n--check: pages are out of date. Run `python3 build_papers.py` and commit.",
            file=sys.stderr,
        )
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(description="Generate per-paper static HTML pages.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any page would change (useful for CI).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file output.",
    )
    args = parser.parse_args()

    exit_code = build_all(check_only=args.check, quiet=args.quiet)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
