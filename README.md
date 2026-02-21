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

- **API Keys** — Scoped access tokens (`bw_` prefix, SHA256 hashed, shown once at creation). Per-document permissions, usage tracking, expiry. Used by both the REST API (`/api/v1/search`) and the MCP endpoint.

- **Admin** — System stats, user management (activate/deactivate/promote), document oversight across all users, invite system with token generation and expiry, registration mode toggle, health monitoring (Postgres + Redis checks).

- **MCP Integration** — Streamable HTTP MCP server at `/mcp/*` with `search_docs` and `find_register` tools (API key authenticated). Also ships as a standalone Claude Code plugin with 5 tools and `/ingest-docs`, `/search-docs` slash commands.

## Quick Start

```bash
cp .env.example .env
# Edit .env — generate secrets: openssl rand -base64 32 (passwords), openssl rand -base64 64 (JWT)
docker compose up --build
```

App at `http://localhost:80`. First user to register becomes admin.

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

## MCP Plugin

```bash
claude plugin add bitwise-embedded-docs
```

Tools: `search_docs`, `find_register`, `list_docs`, `ingest_docs`, `remove_docs`

## Tech Stack

Python 3.11 | FastAPI | Celery | PostgreSQL | Redis | React 19 | TypeScript | Tailwind CSS 4 | Caddy | Shoo | PyMuPDF | pdfplumber | sentence-transformers | FAISS | SQLite FTS5

## License

[MIT](LICENSE)
