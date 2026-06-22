"""
OneNote HTML → Markdown parser using BeautifulSoup.

PRESERVE: title/headings, bullets/numbered lists, checkboxes, tables, links
STRIP:    font styles, colors, absolute positioning, base64 image blobs, inline styles, MS layout noise
REPLACE:  images → [Image: alt], attachments → [Attachment: filename]
"""

import re
from typing import Optional

from bs4 import BeautifulSoup, NavigableString, Tag


def _clean_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def _table_to_md(table: Tag) -> str:
    rows = table.find_all("tr")
    if not rows:
        return ""
    md_rows = []
    for i, row in enumerate(rows):
        cells = row.find_all(["td", "th"])
        cell_texts = [_clean_text(cell.get_text(" ", strip=True)) for cell in cells]
        md_rows.append("| " + " | ".join(cell_texts) + " |")
        if i == 0:
            md_rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(md_rows)


def _process_node(node, depth: int = 0) -> str:
    if isinstance(node, NavigableString):
        text = str(node)
        if text.strip():
            return text
        return ""

    if not isinstance(node, Tag):
        return ""

    tag = node.name.lower() if node.name else ""

    # Skip MS layout noise
    if tag in ("style", "script", "meta", "head"):
        return ""

    # Images → placeholder
    if tag == "img":
        alt = node.get("alt", "")
        src = node.get("src", "")
        # Skip base64 blobs
        if src.startswith("data:"):
            return f"[Image: {alt}]\n" if alt else "[Image]\n"
        return f"[Image: {alt or src}]\n"

    # Attachments (object tag)
    if tag == "object":
        data_ref = node.get("data-attachment", node.get("data", ""))
        return f"[Attachment: {data_ref}]\n"

    # Links
    if tag == "a":
        href = node.get("href", "")
        inner = "".join(_process_node(c) for c in node.children).strip()
        if href and inner:
            return f"[{inner}]({href})"
        return inner

    # Headings
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(tag[1])
        inner = "".join(_process_node(c) for c in node.children).strip()
        return f"\n{'#' * level} {inner}\n"

    # Paragraphs / div
    if tag in ("p", "div"):
        inner = "".join(_process_node(c) for c in node.children).strip()
        if not inner:
            return ""
        return f"\n{inner}\n"

    # Unordered list
    if tag == "ul":
        items = []
        for li in node.find_all("li", recursive=False):
            inner = "".join(_process_node(c) for c in li.children).strip()
            items.append(f"- {inner}")
        return "\n" + "\n".join(items) + "\n"

    # Ordered list
    if tag == "ol":
        items = []
        for idx, li in enumerate(node.find_all("li", recursive=False), start=1):
            inner = "".join(_process_node(c) for c in li.children).strip()
            items.append(f"{idx}. {inner}")
        return "\n" + "\n".join(items) + "\n"

    # Checkboxes (OneNote uses <input type="checkbox">)
    if tag == "input" and node.get("type") == "checkbox":
        checked = "x" if node.get("checked") else " "
        return f"[{checked}] "

    # Tables
    if tag == "table":
        return "\n" + _table_to_md(node) + "\n"

    # Bold / strong — preserve semantics as markdown
    if tag in ("b", "strong"):
        inner = "".join(_process_node(c) for c in node.children).strip()
        return f"**{inner}**" if inner else ""

    # Italic
    if tag in ("i", "em"):
        inner = "".join(_process_node(c) for c in node.children).strip()
        return f"_{inner}_" if inner else ""

    # Line break
    if tag == "br":
        return "\n"

    # Span and other inline containers — pass through text, strip style noise
    inner = "".join(_process_node(c) for c in node.children)
    return inner


def parse_onenote_html(html: bytes, max_chars: Optional[int] = None) -> str:
    """Convert OneNote output HTML to clean markdown.

    Args:
        html:      raw HTML bytes from Graph /content endpoint
        max_chars: optional hard cap on output length

    Returns:
        Clean markdown string.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove all <style> blocks and inline style attributes
    for tag in soup.find_all(True):
        tag.attrs = {k: v for k, v in (tag.attrs or {}).items() if k not in ("style", "class", "id")}
    for style_tag in soup.find_all("style"):
        style_tag.decompose()

    body = soup.find("body") or soup
    lines = []
    for child in body.children:
        chunk = _process_node(child)
        if chunk:
            lines.append(chunk)

    md = "".join(lines)
    # Collapse runs of 3+ blank lines to 2
    md = re.sub(r"\n{3,}", "\n\n", md).strip()

    if max_chars and len(md) > max_chars:
        md = md[:max_chars] + "\n\n…[truncated]"

    return md
