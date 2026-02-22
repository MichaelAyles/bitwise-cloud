# Bitwise

Hosted search for embedded systems documentation. Upload PDF reference manuals, automatically extract register definitions and memory maps, then search across your datasheets with hybrid keyword + semantic retrieval. Built for engineers who are tired of Ctrl+F through 2000-page MCU manuals.

## Architecture

```
Internet → Cloudflare Tunnel (HTTPS + DDoS) → cloudflared
                                                    ↓
                                              Caddy (:80)
                                         ┌──────┼──────┐
                                    /api/*   /mcp/*     /*
                                         ↓      ↓       ↓
                                       FastAPI        React SPA
                                         ↓
                                   Celery workers
                                         ↓
                              PDF → Parse → Chunk → Embed
                                         ↓
                             FAISS (vectors) + SQLite (FTS5)
```

**Services**: Postgres (users, docs, API keys, invites), Redis (Celery broker), Caddy (reverse proxy + SPA), FastAPI backend (REST + MCP), Celery worker (PDF ingestion, concurrency 2)

**Data isolation**: Each user gets their own index directory. Each document gets its own FAISS + SQLite index pair. API keys can be scoped to specific document subsets.

```
/data/uploads/{user_id}/{doc_id}.pdf
/data/indices/{user_id}/vectors_{doc_id}.faiss
/data/indices/{user_id}/metadata_{doc_id}.db
```

## Features

- **PDF Ingestion** — Async Celery pipeline: PyMuPDF extracts text preserving layout and TOC hierarchy, pdfplumber detects register tables and memory maps, structured extraction to Register/BitField objects, semantic chunking (2500-char target, 200-char overlap, tables kept whole), bge-small-en-v1.5 embeddings (384-dim, CPU), per-document FAISS + SQLite FTS5 indices. Frontend polls for real-time progress.

- **Hybrid Search** — 60% semantic similarity (FAISS) + 40% keyword matching (FTS5). Results appearing in both channels get a 1.2x boost. Register lookup by exact name returns structured data (address, offset, bitfields, peripheral).

- **Auth** — JWT access tokens (15 min) + refresh tokens (7 days, httponly cookie). Google sign-in via [Shoo](https://shoo.dev) (PKCE OAuth, ES256 JWKS verification). Invite-only or open registration, admin role. OAuth users auto-created on first sign-in, linked to existing accounts by verified email.

- **API Keys** — Scoped access tokens (`bw_` prefix, SHA256 hashed, shown once at creation). Per-document permissions, usage tracking, expiry. Used by both the REST API (`/api/v1/search`) and the MCP endpoint. On creation, shows ready-to-copy MCP and REST API usage snippets with the key pre-filled.

- **Admin** — System stats, user management (activate/deactivate/promote), document oversight across all users, invite system with token generation and expiry, registration mode toggle, health monitoring (Postgres + Redis checks).

- **MCP Integration** — Streamable HTTP MCP server at `/mcp/*` with `search_docs` and `find_register` tools (API key authenticated). Also ships as a standalone Claude Code plugin with 5 tools and `/ingest-docs`, `/search-docs` slash commands.

- **In-App Setup Guide** — After signing in, the `/setup` page walks through three steps: upload a datasheet, create an API key, and connect your tools (with tabbed MCP/REST/plugin code snippets using the correct deployment URL). The landing page feature cards also include code snippet previews.

## Quick Start

```bash
cp .env.example .env
# Edit .env — generate secrets: openssl rand -base64 32 (passwords), openssl rand -base64 64 (JWT)
docker compose up --build
```

App at `http://localhost:80`. First user to register becomes admin. After signing in, visit `/setup` for a step-by-step integration guide.

## API

| Group | Endpoints | Auth |
|-------|-----------|------|
| Auth | `POST register`, `login`, `oauth/shoo`, `refresh`; `GET settings` | Public (rate-limited) |
| Users | `GET /me`, `PATCH /me` | JWT |
| Documents | `POST upload`, `GET list`, `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`, `GET /{id}/progress` | JWT |
| Search | `POST /search`, `POST /search/register` | JWT |
| Search (v1) | `POST /v1/search`, `POST /v1/register` | API Key |
| API Keys | `POST create`, `GET list`, `GET /{id}`, `PATCH /{id}`, `PUT /{id}/documents`, `DELETE /{id}` | JWT |
| Admin | Stats, users CRUD, documents CRUD, invites CRUD, settings | JWT (admin) |
| Health | `GET /health` | Public |

## OAuth (Shoo)

Google sign-in uses [Shoo](https://shoo.dev) as an OAuth intermediary. The frontend SDK (`@shoojs/react`) handles PKCE code exchange and identity persistence. Key implementation details:

- The SDK's `handleCallback()` does a full-page redirect after code exchange, so OAuth state must survive page reloads (use `sessionStorage`, not `useRef`)
- `requestPii: true` must be passed to `useShooAuth()` or the identity token won't include email/name claims
- The backend verifies the identity token using Shoo's JWKS endpoint (`ES256`), checking `audience: origin:{PUBLIC_HOST}` and `issuer: https://shoo.dev`
- Auth API endpoints (`login`, `register`, `oauthShoo`) use `skipAuthRetry` to prevent the API client's automatic 401 refresh logic from swallowing actual errors

## Deployment

Cloudflare Tunnel to a Linux box. No open ports. GitHub Actions builds + smoke tests on push to `main`, tags `:latest` only after health check passes. Watchtower auto-pulls within 60s.

```
git push main → CI (black + mypy + build + smoke test) → GHCR → Watchtower → live
```

Immutable `:sha-<commit>` tags on every build enable rollback. See [docs/deploy.md](docs/deploy.md) for full setup, rollback, and backup procedures.

## Integration

### Hosted MCP Server

Connect Claude Code (or any MCP client) to your Bitwise deployment. Add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "bitwise": {
      "type": "streamable-http",
      "url": "https://your-host/mcp",
      "headers": {
        "X-API-Key": "bw_your_api_key"
      }
    }
  }
}
```

### REST API

```bash
curl -H "X-API-Key: bw_..." https://your-host/api/v1/search?q=UART+baud+rate
```

### Claude Code Plugin (Standalone)

The standalone Claude Code plugin lets you search your datasheets directly from Claude Code without the web app. It runs an MCP server locally with the full ingestion and search pipeline.

#### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)

#### Setup

```bash
# Clone the repo and install the engine dependencies
git clone https://github.com/MichaelAyles/bitwise-cloud.git
cd bitwise-cloud
poetry install

# Load the plugin in Claude Code
claude --plugin-dir ./plugins/bitwise-embedded-docs
```

On first run, the embedding model (`bge-small-en-v1.5`, ~130MB) downloads automatically.

#### Usage

Once the plugin is loaded, you get two slash commands and five MCP tools:

**Slash commands** (user-invoked):
- `/bitwise-embedded-docs:ingest-docs` — Guided PDF ingestion
- `/bitwise-embedded-docs:search-docs` — Guided search

**MCP tools** (Claude uses automatically):
- `search_docs(query, top_k, doc_filter)` — Hybrid keyword + semantic search
- `find_register(name, peripheral)` — Exact register lookup
- `list_docs()` — List indexed documents with chunk/register counts
- `ingest_docs(doc_path, title, version)` — Ingest a PDF into the local index
- `remove_docs(doc_id)` — Remove a document from the index

#### Standalone CLI

You can also use the engine outside Claude Code:

```bash
poetry run mcp-embedded-docs ingest path/to/datasheet.pdf --title "MCP2515"
poetry run mcp-embedded-docs list
poetry run mcp-embedded-docs serve   # Start MCP server on stdio
```

#### Configuration

Optionally create a `config.yaml` in the project root to override defaults:

```yaml
chunking:
  target_size: 2500    # chars per chunk
  overlap: 200         # overlap between chunks
search:
  keyword_weight: 0.4
  semantic_weight: 0.6
embeddings:
  model: BAAI/bge-small-en-v1.5
  device: cpu
```

#### Plugin structure

```
plugins/bitwise-embedded-docs/
├── .claude-plugin/
│   └── plugin.json        # Plugin metadata (name, version, description)
├── .mcp.json              # MCP server config (runs python -m mcp_embedded_docs serve)
└── skills/
    ├── ingest-docs/
    │   └── SKILL.md       # Guided ingestion skill
    └── search-docs/
        └── SKILL.md       # Guided search skill
```

The plugin delegates to the `mcp_embedded_docs/` engine package, which contains the ingestion pipeline, indexing layer, and retrieval system.

## Tech Stack

Python 3.11 | FastAPI | Celery | PostgreSQL | Redis | React 19 | TypeScript | Tailwind CSS 4 | Caddy | Shoo | PyMuPDF | pdfplumber | sentence-transformers | FAISS | SQLite FTS5

## License

[MIT](LICENSE)
