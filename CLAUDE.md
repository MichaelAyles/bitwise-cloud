# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development
docker compose up --build                         # Run all services locally
docker compose logs -f backend                    # Tail backend logs
docker compose exec postgres psql -U bitwise bitwise  # DB shell

# MCP plugin (standalone)
poetry install                                    # Install dependencies
poetry run mcp-embedded-docs serve                # Start MCP server (stdio)
poetry run mcp-embedded-docs ingest PATH --title "Title"  # Ingest a PDF
poetry run mcp-embedded-docs list                 # List indexed documents

# Testing & linting
poetry run pytest                                 # Run tests
poetry run pytest tests/test_chunker.py -k "test_name"  # Single test
poetry run black mcp_embedded_docs/               # Format
poetry run mypy mcp_embedded_docs/                # Type check

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

## Project Structure

```
backend/
  app/
    api/          # FastAPI route handlers (auth, documents, search, health, admin, api_keys)
    models/       # SQLAlchemy models (user, document, ingestion_job, api_key)
    mcp/          # MCP server endpoint
    engine/       # Adapter bridging backend to mcp_embedded_docs engine
    config.py     # Pydantic settings (env vars)
    database.py   # Async SQLAlchemy engine + session
    worker.py     # Celery app + ingestion tasks
  alembic/        # Database migrations
  Dockerfile      # Backend + worker image (Python 3.11, CPU PyTorch)
frontend/         # React SPA (Vite + TypeScript)
mcp_embedded_docs/  # Standalone MCP plugin (PDF ingestion + search engine)
  tools/          # Tool implementations (lazy-loaded)
  server.py       # FastMCP server entry point
Dockerfile.caddy  # Caddy image (builds frontend, serves SPA + reverse proxy)
Caddyfile         # Caddy config: /api/* → backend, /* → SPA
docker-compose.yml        # Base services (postgres, redis, backend, worker, caddy)
docker-compose.prod.yml   # Production overrides (GHCR images, cloudflared, watchtower)
```

## Architecture

### Backend (FastAPI + Celery)

FastAPI serves the REST API at `/api/*` and MCP at `/mcp/*`. Celery workers handle async PDF ingestion. Auth is JWT-based with invite-only registration.

**Key routes**: `/api/auth/*`, `/api/documents/*`, `/api/search/*`, `/api/health`, `/api/admin/*`, `/api/keys/*`

The health endpoint (`/api/health`) checks Postgres and Redis connectivity, returning `"healthy"` or `"degraded"`.

### MCP Engine (mcp_embedded_docs/)

FastMCP server exposing 5 tools: `search_docs`, `find_register`, `list_docs`, `ingest_docs`, `remove_docs`. Heavy imports are deferred — tool implementations live in `tools/` and only import PDF/ML dependencies when called.

**Ingestion pipeline**:
```
PDF → pdf_parser.py (PyMuPDF) → table_detector.py (pdfplumber) → table_extractor.py
    → chunker.py (semantic chunking) → embedder.py (bge-small-en-v1.5) → FAISS + SQLite FTS5
```

**Search pipeline**: Hybrid keyword (FTS5, weight 0.4) + semantic (FAISS, weight 0.6), with 1.2x boost for results in both channels.

### Deployment

Cloudflare Tunnel → Caddy → backend. GitHub Actions builds and pushes to GHCR on push to `main`. Watchtower auto-pulls on the production server. See `docs/deploy.md`.

Alembic migrations run on backend startup. Single-instance only — needs init container if scaling replicas.

## Config

Backend: Pydantic settings via env vars (see `.env.example`)

MCP plugin: `config.yaml` (optional, falls back to defaults):
- `chunking.target_size`: 2500 chars, `overlap`: 200 chars
- `search.keyword_weight`: 0.4, `semantic_weight`: 0.6
- `embeddings.model`: `BAAI/bge-small-en-v1.5`, `device`: `cpu`

## Plugin

`plugins/bitwise-embedded-docs/` contains the Claude Code plugin with `.mcp.json` entry point and two skills (`/ingest-docs`, `/search-docs`). Bump the version by changing `pyproject.toml` version field.

## Pre-commit Checks (MANDATORY)

**You MUST run these checks before every commit. Do not commit if any check fails.**

```bash
# 1. Format backend Python (must pass — CI runs black --check)
python3 -m black backend/app/

# 2. Type-check backend (must pass — CI runs mypy)
python3 -m mypy backend/app/ --ignore-missing-imports --install-types --non-interactive

# 3. Type-check and build frontend (must pass — CI builds the Docker image)
cd frontend && npx tsc -b --noEmit && npx vite build
```

If `black` or `mypy` are not installed locally, install them: `pip3 install black mypy`

These mirror the CI lint job in `.github/workflows/deploy.yml`. A failed CI build blocks deployment via Watchtower, so never push code that hasn't passed all three checks.

## Adding a New Tool

1. Create `tools/new_tool.py` with an async function returning a markdown string
2. Register in `server.py` with `@mcp.tool()` decorator (docstring becomes the tool description)
3. Use lazy imports inside the tool function to keep server startup fast
