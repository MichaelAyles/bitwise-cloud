# BitWise Cloud

Hosted platform for embedded systems documentation. Upload PDF reference manuals, automatically extract register definitions and memory maps, then search across your datasheets with hybrid keyword + semantic retrieval. Built for engineers who are tired of Ctrl+F through 2000-page MCU manuals.

## Features

- **PDF Ingestion** — Async pipeline parses large reference manuals preserving structure, detects register tables via pdfplumber, extracts to structured JSON with bitfield definitions
- **Hybrid Search** — 60% semantic similarity (FAISS + bge-small-en-v1.5, 384-dim) + 40% keyword matching (SQLite FTS5), with 1.2x relevance boost when a result appears in both channels
- **Register Lookup** — Direct register-by-name search returning structured data (address, offset, bitfields, peripheral)
- **Context-Aware Chunking** — Leaf-section-only chunking with `[Manual > Section > Subsection]` hierarchy prefixes, sentence-boundary splitting (never mid-word), tables kept whole
- **Multi-Tenant** — Per-user document isolation, configurable storage limits (default 5GB), per-document FAISS + SQLite indices
- **API Keys** — Scoped access tokens (`bw_` prefix, SHA256 hashed) with per-document permissions, usage tracking, and expiry
- **React Frontend** — Document management with live ingestion progress, search UI, API key management, admin panel with system health monitoring
- **MCP Integration** — Search your datasheets directly from Claude Code via the `bitwise-embedded-docs` plugin
- **Auth** — JWT access/refresh tokens, invite-only or open registration, admin role

## Architecture

```
Internet → Cloudflare CDN → cloudflared (tunnel)
                                  ↓
React SPA → Caddy ──→ FastAPI (/api/* — 28 endpoints)
                   ├─→ MCP server (/mcp/* — streamable HTTP)
                   └─→ Static frontend (/*)

Celery workers → PDF parse → Table detect → Chunk → Embed → FAISS + SQLite
```

**Services**: Postgres (users, docs, API keys, invites), Redis (Celery broker + cache), Caddy (reverse proxy + SPA), backend (FastAPI + Alembic migrations), worker (Celery, 2 concurrent)

**Storage layout**:
```
/data/uploads/{user_id}/{doc_id}.pdf
/data/indices/{user_id}/vectors_{doc_id}.faiss
/data/indices/{user_id}/metadata_{doc_id}.db
```

## Ingestion Pipeline

```
Upload PDF → validate (magic bytes, size, SHA256 dedup)
  → Celery task queued (status: pending → ingesting)
    → PyMuPDF: extract text with layout, TOC, section hierarchy
    → pdfplumber: detect register tables, memory maps
    → TableExtractor: parse to Register/BitField structures
    → SemanticChunker: leaf sections, 2500-char target, 200-char overlap
    → bge-small-en-v1.5: 384-dim normalized embeddings (CPU, shared singleton)
    → FAISS IndexFlatL2 + SQLite FTS5 per-document indices
  → status: ready (page_count, chunk_count, register_count)
```

Frontend polls `/api/documents/{id}/progress` for real-time ingestion updates.

## Quick Start

```bash
cp .env.example .env
# Edit .env — generate secrets with: openssl rand -base64 32
docker compose up --build
```

App at `http://localhost:80`. First user to register becomes admin (or set invite-only mode after).

## API

**Auth**: register, login, refresh tokens (httponly cookie), registration settings

**Documents**: upload PDF, list, get, update title, delete, ingestion progress

**Search**: hybrid query + register lookup — both JWT-authenticated (`/api/search`) and API-key-authenticated (`/api/v1/search`) variants

**API Keys**: create (returns key once), list, update, scope to specific documents, revoke

**Admin**: system stats, user management (activate/deactivate/promote), document oversight, invite system, registration mode toggle, system settings

**Health**: `/api/health` — checks Postgres + Redis, returns 200 (healthy) or 503 (degraded)

## Production Deployment

Cloudflare Tunnel to a Linux box. No open ports, Cloudflare handles HTTPS + DDoS.

```
git push main → GitHub Actions (lint + build + smoke test) → GHCR → Watchtower auto-pulls within 60s
```

See [docs/deploy.md](docs/deploy.md) for setup guide, rollback procedure, and backup strategy.

## MCP Plugin

```bash
claude plugin add bitwise-embedded-docs
```

Tools: `search_docs`, `find_register`, `list_docs`, `ingest_docs`, `remove_docs`
Slash commands: `/ingest-docs`, `/search-docs`

## Tech Stack

Python 3.11 | FastAPI | Celery | PostgreSQL | Redis | React 19 | TypeScript | Tailwind CSS | Caddy | PyMuPDF | pdfplumber | sentence-transformers | FAISS | SQLite FTS5

## License

[MIT](LICENSE)
