"""
Allowlist loading and enforcement.

Config lives at /data/allowlist.json (default deny).
A notebook in allowed_notebooks does NOT automatically allow all its sections.
A section is only accessible if both its section_id AND its parent notebook_id are listed.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ALLOWLIST_PATH = Path(os.getenv("DATA_DIR", "/data")) / "allowlist.json"

_DEFAULT_ALLOWLIST = {
    "allowed_notebooks": [],
    "allowed_sections": [],
    "default_deny": True,
}

# Module-level cache; reloaded on startup and on onenote_refresh_index
_allowlist: dict = {}


def load_allowlist() -> None:
    global _allowlist
    if _ALLOWLIST_PATH.exists():
        try:
            _allowlist = json.loads(_ALLOWLIST_PATH.read_text(encoding="utf-8"))
            nb_count = len(_allowlist.get("allowed_notebooks", []))
            sec_count = len(_allowlist.get("allowed_sections", []))
            logger.info("Allowlist loaded: %d notebooks, %d sections", nb_count, sec_count)
        except Exception as exc:
            logger.error("Failed to load allowlist: %s — using default deny", exc)
            _allowlist = dict(_DEFAULT_ALLOWLIST)
    else:
        logger.warning("Allowlist file not found at %s — using default deny", _ALLOWLIST_PATH)
        _allowlist = dict(_DEFAULT_ALLOWLIST)


def write_default_allowlist() -> None:
    _ALLOWLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _ALLOWLIST_PATH.exists():
        _ALLOWLIST_PATH.write_text(
            json.dumps(_DEFAULT_ALLOWLIST, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Default allowlist written to %s", _ALLOWLIST_PATH)


def is_notebook_allowed(notebook_id: str) -> bool:
    for nb in _allowlist.get("allowed_notebooks", []):
        if nb.get("id") == notebook_id:
            return True
    return False


def is_section_allowed(section_id: str, notebook_id: str) -> bool:
    if not is_notebook_allowed(notebook_id):
        return False
    for sec in _allowlist.get("allowed_sections", []):
        if sec.get("id") == section_id and sec.get("notebook_id") == notebook_id:
            return True
    return False


def filter_pages_by_allowlist(pages: list[dict]) -> list[dict]:
    """Remove pages whose section or notebook is not in the allowlist."""
    allowed = []
    for page in pages:
        if is_section_allowed(page.get("section_id", ""), page.get("notebook_id", "")):
            allowed.append(page)
    return allowed


def assert_page_allowed(section_id: str, notebook_id: str) -> Optional[dict]:
    """Return None if allowed, or an error dict if denied."""
    if not is_section_allowed(section_id, notebook_id):
        return {
            "error": True,
            "error_type": "allowlist_error",
            "message": "Page or section is not in the approved access scope.",
        }
    return None


def get_allowed_section_ids() -> list[str]:
    return [s["id"] for s in _allowlist.get("allowed_sections", [])]


def get_allowed_notebook_ids() -> list[str]:
    return [n["id"] for n in _allowlist.get("allowed_notebooks", [])]
