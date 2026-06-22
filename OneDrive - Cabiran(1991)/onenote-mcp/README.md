# OneNote MCP Context Server

Remote MCP server connecting Claude to Shani's OneNote (Cabiran work account) via Microsoft Graph.

- **Transport**: HTTP/SSE (remote, not local stdio)
- **Scope**: `Notes.Read` only — no write, no other Graph permissions
- **Tenant**: Single-tenant Cabiran (Microsoft Entra ID)
- **Hosting**: Render with persistent disk

---

## Prerequisites

- Python 3.11+
- A Render account with a **persistent disk** mounted at `/data`
- An app registration in Cabiran's Azure AD with `Notes.Read` delegated permission and a redirect URI pointing to `/auth/callback`

---

## Setup Steps

### 1. Clone and install

```bash
git clone https://github.com/shanimosco47-pixel/onenote-mcp
cd onenote-mcp
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` (local dev) or set in Render dashboard:

| Variable | Description |
|---|---|
| `AZURE_CLIENT_ID` | App registration client ID from Cabiran Azure AD |
| `AZURE_TENANT_ID` | Cabiran tenant ID |
| `AZURE_CLIENT_SECRET` | App registration client secret |
| `AZURE_REDIRECT_URI` | `https://onenote-mcp.onrender.com/auth/callback` |
| `MSAL_CACHE_KEY` | Fernet key for token cache encryption — see below |
| `MCP_API_KEY` | Shared secret for Claude ↔ MCP server auth |
| `BASE_URL` | `https://onenote-mcp.onrender.com` |
| `DATA_DIR` | `/data` (Render persistent disk mount point) |

**Generate the Fernet key once:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store the output as `MSAL_CACHE_KEY` in Render. Never commit it.

### 3. Deploy to Render

1. Connect the GitHub repo in Render.
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Attach a **persistent disk** at mount path `/data`.
5. Add all environment variables from step 2.

### 4. Authenticate

Open in a browser (sign in with your Cabiran work account):

```
https://onenote-mcp.onrender.com/auth/login
```

Verify the session:

```
https://onenote-mcp.onrender.com/auth/status
```

### 5. Configure the allowlist

The server starts with default deny. No notebook or section is accessible until you add it.

Edit `/data/allowlist.json` on the Render persistent disk (via Render shell or SSH):

```json
{
  "allowed_notebooks": [
    { "id": "<notebook-graph-id>", "display_name": "Work - Shani" }
  ],
  "allowed_sections": [
    { "id": "<section-graph-id>", "display_name": "Active", "notebook_id": "<notebook-graph-id>" },
    { "id": "<section-graph-id>", "display_name": "השבוע", "notebook_id": "<notebook-graph-id>" }
  ],
  "default_deny": true
}
```

To find your notebook and section IDs, call Graph directly after auth:

```
GET https://graph.microsoft.com/v1.0/me/onenote/notebooks
GET https://graph.microsoft.com/v1.0/me/onenote/sections
```

Or use [Graph Explorer](https://developer.microsoft.com/graph/graph-explorer) signed in with your Cabiran account.

### 6. Build the index

Tell Claude (or call directly):

```
onenote_refresh_index(force=false)
```

This is the only time you need to call this manually. Normal conversations use per-call metadata sync.

### 7. Connect Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "onenote": {
      "url": "https://onenote-mcp.onrender.com/mcp",
      "headers": {
        "X-MCP-Key": "<value of MCP_API_KEY>"
      }
    }
  }
}
```

---

## MCP Tools

| Tool | Purpose |
|---|---|
| `onenote_week_context` | PRIMARY — returns pages modified in last N days and/or active pages |
| `onenote_search_pages` | Find pages by keyword, date filter, section, or notebook |
| `onenote_get_page` | Fetch one page as clean markdown |
| `onenote_refresh_index` | **Manual only** — rebuild metadata index |

Every response includes `source_page_title`, `lastModifiedTime`, and `cache_status`.

### Cache status values

| Value | Meaning |
|---|---|
| `fresh` | Fetched from Graph this call |
| `cached` | Served from SQLite; content unchanged since last fetch |
| `stale` | Graph was unavailable; serving last known content |

---

## Auth Endpoints

| Endpoint | Description |
|---|---|
| `GET /auth/login` | Open in browser to start OAuth flow |
| `GET /auth/callback` | Microsoft redirect target — do not call manually |
| `GET /auth/status` | Check current session (no token values returned) |
| `POST /auth/logout` | Clear local token cache |

---

## Architecture

```
Claude Desktop / Claude Code
        │  HTTPS + X-MCP-Key
        ▼
  FastAPI (Render)
    /mcp  ← FastMCP SSE transport
    /auth ← OAuth2 flow
        │
        ├── MSAL token cache → /data/token_cache.bin (Fernet-encrypted)
        ├── SQLite cache    → /data/onenote_cache.db
        ├── Allowlist       → /data/allowlist.json
        │
        ▼
  Microsoft Graph v1.0 (Notes.Read only)
        │
        ▼
  Cabiran OneNote
```

---

## Security Notes

- Tokens are **never** stored as plain JSON, never logged, never passed to Claude.
- `MSAL_CACHE_KEY` lives only in the Render environment variable — not in source code or `.env` files.
- The allowlist enforces default deny — pages outside the approved scope return an explicit error, not empty results.
- Claude never calls `onenote_refresh_index` automatically.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| All tool calls return `allowlist_error` | Configure `/data/allowlist.json` (step 5 above) |
| `index_empty` error | Run `onenote_refresh_index` (step 6 above) |
| `auth_error` / `reauth_required` | Open `/auth/login` again |
| Token cache lost after redeploy | Confirm Render persistent disk is attached at `/data` |
| `MSAL_CACHE_KEY` not set | Set the env var in Render dashboard |
