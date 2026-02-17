# BitWise Cloud

Hosted platform for embedded systems documentation. Ingest PDF reference manuals, extract register definitions, and search across your datasheets with hybrid keyword + semantic retrieval. Includes a React frontend, FastAPI backend, Celery workers, and an MCP plugin for Claude Code integration.

## Features

- **PDF Ingestion** — Parses large reference manuals preserving structure, extracts register tables to structured JSON
- **Hybrid Search** — Combines keyword matching (SQLite FTS5) with semantic similarity (FAISS + bge-small-en-v1.5)
- **Context-Aware Chunking** — Section hierarchy prefixes, sentence-aware splitting, content deduplication
- **React Frontend** — Document management, search UI, API key management, admin panel
- **REST API + MCP** — FastAPI backend with Celery async ingestion, plus MCP endpoint for Claude Code
- **Auth** — JWT auth with invite-only registration, admin mode

## Architecture

```
React SPA → Caddy → FastAPI (/api/*)
                  → MCP server (/mcp/*)
                  → Static frontend (/*)

Celery workers → PDF parsing → Embedding → FAISS + SQLite indexing
```

**Services**: Postgres (data), Redis (queue/cache), Caddy (reverse proxy + SPA), backend (API), worker (ingestion)

## Quick Start (Development)

```bash
cp .env.example .env
# Edit .env with your values (openssl rand -base64 32 for secrets)
docker compose up --build
```

App runs at `http://localhost:80`. Backend API at `http://localhost:80/api/`.

## Production Deployment

Deploys via Cloudflare Tunnel to a Linux box. Push to `main` → GitHub Actions builds images → Watchtower auto-pulls on the server.

See [docs/deploy.md](docs/deploy.md) for full setup guide.

```bash
# On the production server:
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## MCP Plugin

Install the Claude Code plugin for in-editor documentation search:

```bash
claude plugin add bitwise-embedded-docs
```

Provides `search_docs`, `find_register`, `list_docs`, `ingest_docs`, `remove_docs` tools plus `/ingest-docs` and `/search-docs` slash commands.

## Tech Stack

Python 3.11 | FastAPI | Celery | PostgreSQL | Redis | React | Caddy | PyMuPDF | pdfplumber | sentence-transformers | FAISS | SQLite FTS5

## License

[MIT](LICENSE)
