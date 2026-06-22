# Decisions

## 2026-06-22: MCP transport — remote HTTP/SSE, not local stdio

### Decision
Use FastMCP's ASGI app mounted at `/mcp`, deployed on Render, reached over HTTPS with SSE transport.

### Context
The spec requires "remote MCP over HTTP/SSE" and a Render deployment. Claude Desktop connects via URL + X-MCP-Key header, not via local stdio process.

### Reason
Matches spec §6.1 exactly. Single server instance holds the Microsoft OAuth session; Claude never sees Microsoft tokens.

### Consequences
Requires a persistent disk on Render for `/data`. Cold starts on Render free tier will delay the first tool call.

---

## 2026-06-22: Allowlist — section-level double check required

### Decision
A notebook entry in `allowed_notebooks` does NOT grant access to its sections. Each section must also appear in `allowed_sections` with its `notebook_id`.

### Context
Spec §7.2 states this explicitly to prevent accidental access to new sections added to an allowed notebook.

### Reason
Principle of least privilege. Default deny.

### Consequences
After adding a new section to OneNote, `allowlist.json` must be updated manually before Claude can access it.

---

## 2026-06-22: Token cache — Fernet on persistent disk, no plain JSON

### Decision
MSAL SerializableTokenCache is serialized, Fernet-encrypted with `MSAL_CACHE_KEY`, and written to `/data/token_cache.bin`.

### Context
Spec §5.1 lists plain JSON as explicitly not acceptable. Render's ephemeral filesystem means the disk must be mounted as persistent.

### Reason
Tokens at rest must be encrypted. Key lives only in the Render environment variable.

### Consequences
Losing `MSAL_CACHE_KEY` or the persistent disk invalidates the token cache and requires re-auth.

---

## 2026-06-22: onenote_refresh_index — manual trigger only, 500-page cap

### Decision
`onenote_refresh_index` is never called automatically. It respects Retry-After on 429. Hard cap of 500 pages regardless of allowlist size.

### Context
Spec §3.5 lists these as enforced in code, not convention.

### Reason
Prevents accidental Graph API quota exhaustion and avoids background jobs on Render.

### Consequences
Index can become stale if Shani forgets to refresh. Mitigated by per-conversation metadata sync in `onenote_week_context`.
