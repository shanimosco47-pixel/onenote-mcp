"""
SQLite cache at /data/onenote_cache.db.

Tables:
  page_metadata  — one row per OneNote page (id, title, section, notebook, lastModifiedTime, retrieved_at)
  page_content   — parsed markdown content keyed by page_id + lastModifiedTime
"""

import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

_DB_PATH = Path(os.getenv("DATA_DIR", "/data")) / "onenote_cache.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS page_metadata (
    page_id            TEXT PRIMARY KEY,
    title              TEXT NOT NULL,
    section_id         TEXT NOT NULL,
    section_name       TEXT NOT NULL,
    notebook_id        TEXT NOT NULL,
    notebook_name      TEXT NOT NULL,
    last_modified_time TEXT NOT NULL,
    retrieved_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS page_content (
    page_id            TEXT NOT NULL,
    last_modified_time TEXT NOT NULL,
    markdown           TEXT NOT NULL,
    parsed_at          TEXT NOT NULL,
    PRIMARY KEY (page_id, last_modified_time)
);
"""


async def init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()
    logger.info("SQLite cache initialized at %s", _DB_PATH)


async def upsert_page_metadata(
    page_id: str,
    title: str,
    section_id: str,
    section_name: str,
    notebook_id: str,
    notebook_name: str,
    last_modified_time: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO page_metadata
                (page_id, title, section_id, section_name, notebook_id, notebook_name, last_modified_time, retrieved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(page_id) DO UPDATE SET
                title              = excluded.title,
                section_id         = excluded.section_id,
                section_name       = excluded.section_name,
                notebook_id        = excluded.notebook_id,
                notebook_name      = excluded.notebook_name,
                last_modified_time = excluded.last_modified_time,
                retrieved_at       = excluded.retrieved_at
            """,
            (page_id, title, section_id, section_name, notebook_id, notebook_name, last_modified_time, now),
        )
        await db.commit()


async def get_page_metadata(page_id: str) -> Optional[dict]:
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM page_metadata WHERE page_id = ?", (page_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_cached_content(page_id: str, last_modified_time: str) -> Optional[str]:
    async with aiosqlite.connect(_DB_PATH) as db:
        async with db.execute(
            "SELECT markdown FROM page_content WHERE page_id = ? AND last_modified_time = ?",
            (page_id, last_modified_time),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def upsert_page_content(page_id: str, last_modified_time: str, markdown: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO page_content (page_id, last_modified_time, markdown, parsed_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(page_id, last_modified_time) DO UPDATE SET
                markdown  = excluded.markdown,
                parsed_at = excluded.parsed_at
            """,
            (page_id, last_modified_time, markdown, now),
        )
        await db.commit()


async def get_recent_pages(days: int, limit: int) -> list[dict]:
    """Return page metadata for pages modified in the last N days, newest first."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM page_metadata
            WHERE last_modified_time >= ?
            ORDER BY last_modified_time DESC
            LIMIT ?
            """,
            (cutoff, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def search_pages_by_title(query: str, limit: int) -> list[dict]:
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM page_metadata
            WHERE title LIKE ?
            ORDER BY last_modified_time DESC
            LIMIT ?
            """,
            (f"%{query}%", limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def count_indexed_pages() -> int:
    async with aiosqlite.connect(_DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM page_metadata") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def clear_index() -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("DELETE FROM page_metadata")
        await db.execute("DELETE FROM page_content")
        await db.commit()
    logger.info("SQLite index cleared")
