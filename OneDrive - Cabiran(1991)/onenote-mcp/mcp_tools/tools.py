"""
MCP tool definitions.

Tools:
  onenote_week_context   — primary: returns current working set
  onenote_search_pages   — find pages by keyword or filter
  onenote_get_page       — fetch one page as markdown
  onenote_refresh_index  — manual index rebuild only

Every successful response includes source_page_title, lastModifiedTime, cache_status.
All fetches are bounded by the allowlist (default deny).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from allowlist import (
    assert_page_allowed,
    filter_pages_by_allowlist,
    get_allowed_section_ids,
    load_allowlist,
)
from db.cache import (
    count_indexed_pages,
    get_cached_content,
    get_page_metadata,
    get_recent_pages,
    search_pages_by_title,
    upsert_page_content,
    upsert_page_metadata,
)
from graph.client import get_onenote_pages, get_page_html
from parser.html_to_md import parse_onenote_html

logger = logging.getLogger(__name__)

_MAX_PAGES_HARD_LIMIT = 500

# Section names that indicate active strategic content
_ACTIVE_SECTION_NAMES = {"Active", "השבוע", "נושאים פתוחים", "הנהלה"}
_ACTIVE_TITLE_PREFIXES = ("ACTIVE:", "MOD:", "השבוע:", "🔥")


def _is_active_page(page: dict) -> bool:
    section_name = page.get("section_name", "")
    title = page.get("title", "")
    if section_name in _ACTIVE_SECTION_NAMES:
        return True
    for prefix in _ACTIVE_TITLE_PREFIXES:
        if title.startswith(prefix):
            return True
    return False


def _build_page_result(meta: dict, markdown: str, cache_status: str) -> dict:
    return {
        "page_id": meta["page_id"],
        "source_page_title": meta["title"],
        "section": meta["section_name"],
        "notebook": meta.get("notebook_name", ""),
        "lastModifiedTime": meta["last_modified_time"],
        "retrieved_at": meta.get("retrieved_at", ""),
        "cache_status": cache_status,
        "content": markdown,
    }


async def _fetch_and_cache_page(page_id: str, last_modified_time: str) -> tuple[str, str]:
    """Return (markdown, cache_status). Fetches from Graph if not cached."""
    cached = await get_cached_content(page_id, last_modified_time)
    if cached is not None:
        return cached, "cached"

    html = await get_page_html(page_id)
    if isinstance(html, dict) and html.get("error"):
        return "", "error"
    markdown = parse_onenote_html(html)
    await upsert_page_content(page_id, last_modified_time, markdown)
    return markdown, "fresh"


async def _sync_pages_from_graph(section_ids: list[str], modified_after: Optional[str] = None) -> list[dict]:
    """Pull metadata from Graph, persist to SQLite, return metadata rows."""
    raw_pages = await get_onenote_pages(section_ids, modified_after=modified_after)
    if isinstance(raw_pages, dict) and raw_pages.get("error"):
        return []

    synced: list[dict] = []
    for p in raw_pages:
        page_id = p.get("id", "")
        title = p.get("title", "")
        lmt = p.get("lastModifiedDateTime", "")
        section_id = p.get("parentSection", {}).get("id", "")
        section_name = p.get("parentSection", {}).get("displayName", "")
        notebook_id = p.get("parentNotebook", {}).get("id", "")
        notebook_name = p.get("parentNotebook", {}).get("displayName", "")

        if not page_id:
            continue

        await upsert_page_metadata(
            page_id=page_id,
            title=title,
            section_id=section_id,
            section_name=section_name,
            notebook_id=notebook_id,
            notebook_name=notebook_name,
            last_modified_time=lmt,
        )
        synced.append({
            "page_id": page_id,
            "title": title,
            "section_id": section_id,
            "section_name": section_name,
            "notebook_id": notebook_id,
            "notebook_name": notebook_name,
            "last_modified_time": lmt,
        })
    return synced


# ──────────────────────────────────────────────
# Tool: onenote_week_context
# ──────────────────────────────────────────────

async def onenote_week_context(
    days: int = 10,
    active_only: bool = False,
    max_pages: int = 20,
) -> dict[str, Any]:
    """Return the current working set: pages modified in the last N days and/or active pages."""
    max_pages = min(max_pages, _MAX_PAGES_HARD_LIMIT)
    allowed_section_ids = get_allowed_section_ids()
    if not allowed_section_ids:
        return {
            "error": True,
            "error_type": "allowlist_error",
            "message": "Allowlist has no allowed sections. Configure /data/allowlist.json and restart.",
        }

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    await _sync_pages_from_graph(allowed_section_ids, modified_after=cutoff)

    candidates = await get_recent_pages(days=days, limit=max_pages * 2)
    candidates = filter_pages_by_allowlist(candidates)

    if active_only:
        candidates = [p for p in candidates if _is_active_page(p)]

    candidates = candidates[:max_pages]

    if not candidates:
        page_count = await count_indexed_pages()
        if page_count == 0:
            return {
                "error": True,
                "error_type": "index_empty",
                "message": "Index has no pages. Run onenote_refresh_index to build it.",
            }
        return {"pages": [], "message": f"No pages found in the last {days} days within allowed scope."}

    pages_out = []
    for meta in candidates:
        markdown, cache_status = await _fetch_and_cache_page(
            meta["page_id"], meta["last_modified_time"]
        )
        if cache_status == "error":
            continue
        pages_out.append(_build_page_result(meta, markdown, cache_status))

    return {
        "pages": pages_out,
        "total_returned": len(pages_out),
        "days_window": days,
    }


# ──────────────────────────────────────────────
# Tool: onenote_search_pages
# ──────────────────────────────────────────────

async def onenote_search_pages(
    query: str = "",
    modified_after: Optional[str] = None,
    notebook_id: Optional[str] = None,
    section_id: Optional[str] = None,
    active_only: bool = False,
    limit: int = 10,
) -> dict[str, Any]:
    """Find pages by keyword or filter, bounded by allowlist."""
    limit = min(limit, _MAX_PAGES_HARD_LIMIT)
    allowed_section_ids = get_allowed_section_ids()
    if not allowed_section_ids:
        return {
            "error": True,
            "error_type": "allowlist_error",
            "message": "Allowlist has no allowed sections.",
        }

    # Narrow to requested section/notebook if specified (still must be in allowlist)
    target_sections = allowed_section_ids
    if section_id:
        target_sections = [s for s in target_sections if s == section_id]
    if notebook_id:
        from allowlist import _allowlist
        target_sections = [
            s["id"] for s in _allowlist.get("allowed_sections", [])
            if s.get("notebook_id") == notebook_id and s["id"] in target_sections
        ]

    if not target_sections:
        return {
            "error": True,
            "error_type": "allowlist_error",
            "message": "Requested notebook/section is not in the approved access scope.",
        }

    await _sync_pages_from_graph(target_sections, modified_after=modified_after)

    if query:
        candidates = await search_pages_by_title(query, limit * 3)
    else:
        candidates = await get_recent_pages(days=365, limit=limit * 3)

    candidates = filter_pages_by_allowlist(candidates)
    if active_only:
        candidates = [p for p in candidates if _is_active_page(p)]
    candidates = candidates[:limit]

    pages_out = []
    for meta in candidates:
        markdown, cache_status = await _fetch_and_cache_page(
            meta["page_id"], meta["last_modified_time"]
        )
        if cache_status == "error":
            continue
        pages_out.append(_build_page_result(meta, markdown, cache_status))

    return {"pages": pages_out, "total_returned": len(pages_out), "query": query}


# ──────────────────────────────────────────────
# Tool: onenote_get_page
# ──────────────────────────────────────────────

async def onenote_get_page(
    page_id: str,
    format: str = "markdown",
    max_chars: int = 20000,
) -> dict[str, Any]:
    """Fetch a single page as clean markdown. Page must be in an allowed section."""
    meta = await get_page_metadata(page_id)
    if not meta:
        return {
            "error": True,
            "error_type": "graph_error",
            "message": f"Page {page_id} not found in index. Run onenote_refresh_index first.",
        }

    denied = assert_page_allowed(meta["section_id"], meta["notebook_id"])
    if denied:
        return denied

    html = await get_page_html(page_id)
    if isinstance(html, dict) and html.get("error"):
        # Try cache fallback
        cached = await get_cached_content(page_id, meta["last_modified_time"])
        if cached:
            return _build_page_result(meta, cached[:max_chars], "stale")
        html_err = dict(html)
        html_err["cache_fallback_available"] = False
        return html_err

    markdown = parse_onenote_html(html, max_chars=max_chars)
    await upsert_page_content(page_id, meta["last_modified_time"], markdown)
    return _build_page_result(meta, markdown, "fresh")


# ──────────────────────────────────────────────
# Tool: onenote_refresh_index
# ──────────────────────────────────────────────

async def onenote_refresh_index(force: bool = False) -> dict[str, Any]:
    """
    Rebuild the metadata index. Manual use only — never called automatically.

    Hard limits:
      - max _MAX_PAGES_HARD_LIMIT pages per refresh
      - only pages in allowed sections
      - pagination via Graph $top / @odata.nextLink
    """
    allowed_section_ids = get_allowed_section_ids()
    if not allowed_section_ids:
        return {
            "error": True,
            "error_type": "allowlist_error",
            "message": "Allowlist has no allowed sections. Configure /data/allowlist.json first.",
        }

    if force:
        from db.cache import clear_index
        await clear_index()
        logger.info("Index cleared (force=True)")

    # Reload allowlist in case it was edited
    load_allowlist()

    synced = await _sync_pages_from_graph(allowed_section_ids)
    total = await count_indexed_pages()

    return {
        "indexed_this_run": len(synced),
        "total_indexed": min(total, _MAX_PAGES_HARD_LIMIT),
        "max_pages_cap": _MAX_PAGES_HARD_LIMIT,
        "allowed_sections": len(allowed_section_ids),
        "cache_status": "fresh",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
