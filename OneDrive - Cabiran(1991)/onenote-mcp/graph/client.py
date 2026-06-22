"""
Microsoft Graph API client for OneNote endpoints.

All errors are returned as structured dicts — never raw exceptions.
Every request sends a client-request-id (correlation_id) header.
Retry-After is respected on 429 responses.
"""

import asyncio
import logging
import uuid
from typing import Any, Optional

import httpx
from auth.token_cache import SCOPES, build_msal_app, load_token_cache, save_token_cache

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Endpoint family labels used in error objects
_FAMILY = {
    "onenote/pages": "onenote_pages",
    "onenote/notebooks": "onenote_notebooks",
    "onenote/sections": "onenote_sections",
    "onenote/pages/{id}/content": "onenote_content",
}


def _endpoint_family(path: str) -> str:
    if "content" in path:
        return "onenote_content"
    if "pages" in path:
        return "onenote_pages"
    if "sections" in path:
        return "onenote_sections"
    if "notebooks" in path:
        return "onenote_notebooks"
    return "unknown"


def _make_error(
    *,
    error_type: str,
    status_code: int,
    endpoint_path: str,
    message: str,
    graph_request_id: str = "",
    correlation_id: str = "",
    retry_count: int = 0,
    retry_after_seconds: Optional[int] = None,
    cache_fallback_available: bool = False,
    cache_last_updated: Optional[str] = None,
) -> dict:
    err: dict[str, Any] = {
        "error": True,
        "error_type": error_type,
        "status_code": status_code,
        "graph_request_id": graph_request_id,
        "correlation_id": correlation_id,
        "endpoint_family": _endpoint_family(endpoint_path),
        "retry_count": retry_count,
        "message": message,
        "cache_fallback_available": cache_fallback_available,
    }
    if retry_after_seconds is not None:
        err["retry_after_seconds"] = retry_after_seconds
    if cache_last_updated:
        err["cache_last_updated"] = cache_last_updated
    return err


def _get_access_token() -> str | dict:
    cache = load_token_cache()
    app = build_msal_app(cache)
    accounts = app.get_accounts()
    if not accounts:
        return _make_error(
            error_type="auth_error",
            status_code=401,
            endpoint_path="",
            message="OneNote access needs reauthorization. Open /auth/login to reconnect.",
        )
    result = app.acquire_token_silent(scopes=SCOPES, account=accounts[0])
    save_token_cache(cache)
    if not result or "error" in result:
        return _make_error(
            error_type="auth_error",
            status_code=401,
            endpoint_path="",
            message="OneNote access needs reauthorization. Open /auth/login to reconnect.",
        )
    return result["access_token"]


async def graph_get(path: str, params: Optional[dict] = None) -> dict | list:
    """
    Perform a single GET against Graph. Returns parsed JSON or a structured error dict.
    Retries once on 429 after Retry-After.
    """
    token = _get_access_token()
    if isinstance(token, dict) and token.get("error"):
        return token

    correlation_id = str(uuid.uuid4())
    url = f"{_GRAPH_BASE}/{path.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "client-request-id": correlation_id,
    }

    retry_count = 0
    async with httpx.AsyncClient(timeout=15.0) as client:
        for attempt in range(2):
            try:
                resp = await client.get(url, headers=headers, params=params or {})
            except httpx.TimeoutException:
                return _make_error(
                    error_type="timeout",
                    status_code=408,
                    endpoint_path=path,
                    message="Graph API request timed out.",
                    correlation_id=correlation_id,
                    retry_count=retry_count,
                )
            except httpx.RequestError as exc:
                return _make_error(
                    error_type="graph_unavailable",
                    status_code=503,
                    endpoint_path=path,
                    message=f"Network error contacting Graph API: {exc}",
                    correlation_id=correlation_id,
                    retry_count=retry_count,
                )

            graph_request_id = resp.headers.get("request-id", "")

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 429 and attempt == 0:
                retry_after = int(resp.headers.get("Retry-After", "5"))
                logger.warning("Graph 429 on %s — waiting %ds (correlation=%s)", path, retry_after, correlation_id)
                await asyncio.sleep(retry_after)
                retry_count = 1
                continue

            error_type = {
                401: "auth_error",
                403: "auth_error",
                404: "graph_error",
                429: "rate_limit",
                500: "graph_error",
                503: "graph_unavailable",
            }.get(resp.status_code, "graph_error")

            message_map = {
                401: "OneNote access needs reauthorization. Open /auth/login to reconnect.",
                403: "OneNote access needs reauthorization. Open /auth/login to reconnect.",
                404: "Requested OneNote resource was not found.",
                429: "Graph API rate limit reached. Please retry shortly.",
                503: "Graph API is temporarily unavailable.",
            }
            return _make_error(
                error_type=error_type,
                status_code=resp.status_code,
                endpoint_path=path,
                message=message_map.get(resp.status_code, f"Graph API returned {resp.status_code}"),
                graph_request_id=graph_request_id,
                correlation_id=correlation_id,
                retry_count=retry_count,
                retry_after_seconds=int(resp.headers.get("Retry-After", 0)) or None,
            )

    # Should not reach here
    return _make_error(
        error_type="graph_error",
        status_code=500,
        endpoint_path=path,
        message="Unexpected error in graph_get",
        correlation_id=correlation_id,
        retry_count=retry_count,
    )


async def graph_get_raw_bytes(path: str) -> bytes | dict:
    """Fetch raw bytes (used for page HTML content endpoint)."""
    token = _get_access_token()
    if isinstance(token, dict) and token.get("error"):
        return token

    correlation_id = str(uuid.uuid4())
    url = f"{_GRAPH_BASE}/{path.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "client-request-id": correlation_id,
    }

    retry_count = 0
    async with httpx.AsyncClient(timeout=20.0) as client:
        for attempt in range(2):
            try:
                resp = await client.get(url, headers=headers)
            except httpx.TimeoutException:
                return _make_error(
                    error_type="timeout",
                    status_code=408,
                    endpoint_path=path,
                    message="Graph API content request timed out.",
                    correlation_id=correlation_id,
                    retry_count=retry_count,
                )
            except httpx.RequestError as exc:
                return _make_error(
                    error_type="graph_unavailable",
                    status_code=503,
                    endpoint_path=path,
                    message=f"Network error: {exc}",
                    correlation_id=correlation_id,
                    retry_count=retry_count,
                )

            graph_request_id = resp.headers.get("request-id", "")
            if resp.status_code == 200:
                return resp.content

            if resp.status_code == 429 and attempt == 0:
                retry_after = int(resp.headers.get("Retry-After", "5"))
                await asyncio.sleep(retry_after)
                retry_count = 1
                continue

            error_type = "auth_error" if resp.status_code in (401, 403) else "graph_error"
            return _make_error(
                error_type=error_type,
                status_code=resp.status_code,
                endpoint_path=path,
                message=f"Graph API returned {resp.status_code}",
                graph_request_id=graph_request_id,
                correlation_id=correlation_id,
                retry_count=retry_count,
            )

    return _make_error(
        error_type="graph_error",
        status_code=500,
        endpoint_path=path,
        message="Unexpected error in graph_get_raw_bytes",
        correlation_id=correlation_id,
        retry_count=retry_count,
    )


async def get_onenote_pages(
    section_ids: list[str],
    modified_after: Optional[str] = None,
    top: int = 50,
) -> list[dict] | dict:
    """Fetch page metadata for a list of section IDs, with optional date filter."""
    all_pages: list[dict] = []
    for section_id in section_ids:
        path = f"me/onenote/sections/{section_id}/pages"
        params: dict = {"$select": "id,title,lastModifiedDateTime,parentSection,parentNotebook", "$top": top}
        if modified_after:
            params["$filter"] = f"lastModifiedDateTime ge {modified_after}"

        while True:
            result = await graph_get(path, params)
            if isinstance(result, dict) and result.get("error"):
                logger.warning("Error fetching pages for section %s: %s", section_id, result.get("message"))
                break
            page_list = result.get("value", []) if isinstance(result, dict) else []
            all_pages.extend(page_list)
            next_link = result.get("@odata.nextLink") if isinstance(result, dict) else None
            if not next_link:
                break
            # nextLink is a full URL; extract path+query
            path = next_link.replace(_GRAPH_BASE, "").lstrip("/")
            params = {}

    return all_pages


async def get_page_html(page_id: str) -> bytes | dict:
    return await graph_get_raw_bytes(f"me/onenote/pages/{page_id}/content")
