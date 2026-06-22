"""
OneNote MCP Context Server — FastAPI entry point.

Routes:
  /auth/*   — Microsoft OAuth2 flow
  /mcp      — MCP over HTTP/SSE (remote transport)

Authentication between Claude and this server: X-MCP-Key header.
Microsoft tokens are NEVER surfaced through this API.
"""

import logging
import os

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from allowlist import load_allowlist, write_default_allowlist
from auth.routes import router as auth_router
from db.cache import init_db
from mcp_tools.tools import (
    onenote_get_page,
    onenote_refresh_index,
    onenote_search_pages,
    onenote_week_context,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── FastMCP server ────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="onenote",
    instructions=(
        "OneNote context server for Shani's Cabiran work account. "
        "Provides read-only access to allowed OneNote sections via Microsoft Graph. "
        "Always check /auth/status before making tool calls. "
        "Never call onenote_refresh_index automatically."
    ),
)


@mcp.tool()
async def onenote_week_context_tool(
    days: int = 10,
    active_only: bool = False,
    max_pages: int = 20,
) -> dict:
    """Return current working set: pages modified in the last N days and/or active pages.
    Bounded by allowlist. Every result includes source_page_title, lastModifiedTime, cache_status."""
    return await onenote_week_context(days=days, active_only=active_only, max_pages=max_pages)


@mcp.tool()
async def onenote_search_pages_tool(
    query: str = "",
    modified_after: str = "",
    notebook_id: str = "",
    section_id: str = "",
    active_only: bool = False,
    limit: int = 10,
) -> dict:
    """Find specific pages by keyword or filter. Bounded by allowlist."""
    return await onenote_search_pages(
        query=query,
        modified_after=modified_after or None,
        notebook_id=notebook_id or None,
        section_id=section_id or None,
        active_only=active_only,
        limit=limit,
    )


@mcp.tool()
async def onenote_get_page_tool(
    page_id: str,
    format: str = "markdown",
    max_chars: int = 20000,
) -> dict:
    """Fetch one specific page as clean markdown. Page must be in an allowed notebook/section."""
    return await onenote_get_page(page_id=page_id, format=format, max_chars=max_chars)


@mcp.tool()
async def onenote_refresh_index_tool(force: bool = False) -> dict:
    """Manually rebuild the metadata index. ONLY call when Shani explicitly requests it.
    Never call automatically. Hard cap of 500 pages. Allowlist-bounded."""
    return await onenote_refresh_index(force=force)


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="OneNote MCP Context Server",
    description="Remote MCP server connecting Claude to Shani's OneNote via Microsoft Graph.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])


@app.middleware("http")
async def enforce_mcp_api_key(request: Request, call_next):
    """Require X-MCP-Key on all /mcp/* requests."""
    if request.url.path.startswith("/mcp"):
        expected_key = os.getenv("MCP_API_KEY", "")
        provided_key = request.headers.get("X-MCP-Key", "")
        if not expected_key:
            logger.warning("MCP_API_KEY not set — /mcp endpoint is unprotected")
        elif provided_key != expected_key:
            return Response(content="Unauthorized", status_code=401)
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    write_default_allowlist()
    await init_db()
    load_allowlist()
    logger.info("OneNote MCP server started")


# Mount MCP SSE transport under /mcp
# mcp==1.2.0 exposes SseServerTransport directly; no get_asgi_app() method exists.
_sse_transport = SseServerTransport("/mcp/messages/")


async def _handle_sse(request: Request):
    async with _sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp._mcp_server.run(
            streams[0],
            streams[1],
            mcp._mcp_server.create_initialization_options(),
        )


_mcp_starlette = Starlette(
    routes=[
        Route("/sse", endpoint=_handle_sse),
        Mount("/messages/", app=_sse_transport.handle_post_message),
    ],
)

app.mount("/mcp", _mcp_starlette)
