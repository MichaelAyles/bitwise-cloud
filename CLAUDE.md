# CLAUDE.md

## Pre-commit Checks (MANDATORY)

**Run all three before every commit. CI will reject failures.**

```bash
python3 -m black backend/app/                                                      # Format
python3 -m mypy backend/app/ --ignore-missing-imports --install-types --non-interactive  # Type check
cd frontend && npx tsc -b --noEmit && npx vite build                               # Build frontend
```

Install if missing: `pip3 install black mypy`

## Commands

```bash
# Development
docker compose up --build                         # All services (postgres, redis, backend, worker, caddy)
docker compose logs -f backend                    # Tail backend logs
docker compose logs -f worker                     # Tail worker logs
docker compose exec postgres psql -U bitwise bitwise  # DB shell

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# MCP plugin (standalone, outside Docker)
poetry install
poetry run mcp-embedded-docs serve
poetry run mcp-embedded-docs ingest PATH --title "Title"
poetry run mcp-embedded-docs list
```

## Project Structure

```
backend/
  app/
    api/              # Route handlers
      auth.py         #   register, login, oauth/shoo, refresh, settings
      documents.py    #   upload, list, get, update, delete, progress
      search.py       #   hybrid search + register lookup (JWT and API key variants)
      api_keys.py     #   create, list, update, scope documents, revoke
      admin.py        #   stats, users, documents, invites, settings
      health.py       #   postgres + redis connectivity check
    models/           # SQLAlchemy ORM
      user.py         #   email, password_hash, oauth_provider/sub, is_admin, storage limits
      document.py     #   title, filename, file_hash, status, chunk/register counts
      api_key.py      #   key_hash (SHA256), key_prefix, document scoping (M2M)
      ingestion_job.py #  celery_task_id, progress_percent, progress_message
      invite.py       #   email, token, expires_at, accepted_at
      system_setting.py # key-value store (registration_mode)
    schemas/          # Pydantic request/response models
    services/
      auth_service.py #   JWT create/decode, bcrypt hash/verify
      shoo_service.py #   JWKS fetch + cache, ES256 token verification
    engine/
      adapter.py      #   Multi-tenant bridge to mcp_embedded_docs (embedder singleton, LRU caches)
    mcp/
      server.py       #   FastMCP stateless HTTP (search_docs, find_register tools)
    config.py         # Pydantic settings from env vars
    database.py       # Async SQLAlchemy engine + session factory
    worker/
      celery_app.py   # Celery config (Redis broker)
      tasks.py        # ingest_document, remove_document (sync SQLAlchemy)
    main.py           # FastAPI app factory, CORS, rate limiting, MCP mount
  alembic/            # 3 migrations: initial schema, admin+invites, oauth columns
  Dockerfile          # Python 3.11, CPU-only PyTorch

frontend/
  src/
    App.tsx           # BrowserRouter + AuthProvider + route definitions
    Layout.tsx        # Authenticated page wrapper (header, nav, footer, blueprint grid bg)
    auth.tsx          # AuthProvider context (token persistence, user fetch, login/logout)
    api.ts            # Centralized HTTP client (auto-retry on 401, skipAuthRetry for auth endpoints)
    pages/
      Landing.tsx     # Marketing page (isometric diagram, feature grid, pipeline strip)
      Login.tsx       # Email/password + Google OAuth
      Register.tsx    # Email/password + Google OAuth (invite token support)
      AuthCallback.tsx # Shoo OAuth redirect target (SDK auto-handles code exchange)
      Documents.tsx   # Upload, list, progress polling, delete
      Search.tsx      # Hybrid search with document filtering
      ApiKeys.tsx     # Create, scope, revoke API keys
      Admin.tsx       # Tabs: dashboard, users, documents, invites
    components/
      GoogleSignInButton.tsx  # Shoo SDK integration (sessionStorage for redirect survival)

mcp_embedded_docs/    # Standalone MCP plugin (also used as engine by backend)
  server.py           # FastMCP with 5 tools (lazy imports)
  tools/              # search_docs, find_register, list_docs, ingest_docs, remove_docs
  ingestion/          # pdf_parser (PyMuPDF), table_detector (pdfplumber), table_extractor, chunker
  indexing/           # embedder (bge-small-en-v1.5), vector_store (FAISS), metadata_store (SQLite FTS5)
  retrieval/          # hybrid_search (keyword 0.4 + semantic 0.6, 1.2x cross-channel boost), formatter

plugins/bitwise-embedded-docs/   # Claude Code plugin packaging (.mcp.json, skills)

docker-compose.yml          # Dev: postgres, redis, backend, worker, caddy
docker-compose.prod.yml     # Prod: GHCR images, cloudflared, watchtower, resource limits
Dockerfile.caddy            # Node build stage → Caddy with SPA
Caddyfile                   # /api/* + /mcp/* → backend:8000, /* → SPA with try_files
scripts/backup-postgres.sh  # Daily pg_dump, 14-day retention, optional R2 upload
```

## Architecture

### Backend

FastAPI serves REST at `/api/*` and MCP at `/mcp/*`. Celery workers handle async PDF ingestion. Auth is JWT (HS256, 15-min access + 7-day refresh) with Shoo OAuth support.

**Auth flow**: Password login returns JWT. OAuth flow: frontend SDK (PKCE) → Shoo → callback redirect → SDK persists identity token → GoogleSignInButton sends token to `/api/auth/oauth/shoo` → backend verifies with JWKS (ES256) → creates/links user → returns JWT.

**Key routes**: `/api/auth/*`, `/api/documents/*`, `/api/search/*`, `/api/v1/search/*` (API key), `/api/api-keys/*`, `/api/admin/*`, `/api/health`

**Database**: Async SQLAlchemy (asyncpg) for FastAPI routes. Sync SQLAlchemy (psycopg2) for Celery tasks and MCP handlers. Alembic migrations run on backend startup — safe for single instance only.

### Search Engine

The `mcp_embedded_docs/` package is the core engine, used both as a standalone MCP plugin and imported by the backend via `engine/adapter.py`.

**Ingestion**: PDF → PyMuPDF (text + TOC + layout) → pdfplumber (table detection) → TableExtractor (Register/BitField structs) → SemanticChunker (leaf sections only, tables kept whole, `[Doc > Section > Subsection]` prefixes) → bge-small-en-v1.5 (384-dim, CPU) → per-document FAISS IndexFlatL2 + SQLite FTS5

**Search**: Query → embed → FAISS (top_k*2) + FTS5 (top_k*2) → normalize scores → combine (0.6 semantic + 0.4 keyword) → 1.2x boost if in both → top_k results

**Multi-tenancy**: The adapter maintains a shared embedder singleton (thread-safe) and LRU caches (max 100 each) for vector stores and metadata stores.

### Frontend

React 19 + TypeScript + Tailwind CSS 4. No state management library — just React context (auth) and local useState. Vite dev server proxies `/api/*` and `/mcp/*` to localhost:8000.

**Auth**: AuthProvider wraps the app, restores token from localStorage on mount, validates by calling `/users/me`. Protected routes in Layout redirect unauthenticated users.

**API client** (`api.ts`): Centralized `request<T>()` with auto-retry on 401 (refresh token → retry → redirect to /login). Auth endpoints use `skipAuthRetry: true` so errors surface instead of silently redirecting.

### Deployment

Cloudflare Tunnel → Caddy → backend. No open ports. GitHub Actions: lint (black + mypy) → build images (SHA tag) → smoke test (`/api/health`) → tag `:latest` → Watchtower auto-pulls within 60s.

Prod compose uses `build: !reset null` to disable local builds. Must `docker build` explicitly and tag as `ghcr.io/michaelayles/bitwise-cloud-*:latest`.

## OAuth / Shoo

The frontend uses `@shoojs/react` for Google sign-in. Gotchas learned the hard way:

1. **Redirect survival**: Shoo's `handleCallback()` always calls `window.location.replace()` after code exchange. Any state in `useRef` is lost. Use `sessionStorage` for flags that must survive the redirect.
2. **PII opt-in**: Pass `requestPii: true` to `useShooAuth()`. Without it, the identity token has no `email` or `name` claims, and the backend rejects it with "Token missing required claims".
3. **Auth retry bypass**: `oauthShoo` returns 401 on verification failure. The API client's auto-retry logic (refresh → redirect to /login) must be skipped for auth endpoints, or the actual error is swallowed.
4. **Audience format**: Shoo derives `client_id` as `origin:{window.location.origin}`. Backend must verify with the same format: `origin:{PUBLIC_HOST}`.

## Config

**Backend** (env vars, see `.env.example`): `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `PUBLIC_HOST`, `SHOO_ISSUER`, `SHOO_JWKS_URL`

**MCP plugin** (`config.yaml`, optional): chunking (target 2500, overlap 200), search weights (keyword 0.4, semantic 0.6), embeddings (bge-small-en-v1.5, cpu)

## Adding a New API Endpoint

1. Add route handler in `backend/app/api/`
2. Add Pydantic schemas in `backend/app/schemas/`
3. Register router in `backend/app/api/router.py`
4. Add frontend API method in `frontend/src/api.ts`

## Claude Code Plugin

The plugin at `plugins/bitwise-embedded-docs/` wraps the `mcp_embedded_docs/` engine for use in Claude Code.

**Structure**:
```
plugins/bitwise-embedded-docs/
├── .claude-plugin/plugin.json   # Metadata (name, version 0.2.0)
├── .mcp.json                    # MCP server: python -m mcp_embedded_docs serve
└── skills/
    ├── ingest-docs/SKILL.md     # /bitwise-embedded-docs:ingest-docs
    └── search-docs/SKILL.md     # /bitwise-embedded-docs:search-docs
```

**Testing locally**: `claude --plugin-dir ./plugins/bitwise-embedded-docs`

**Version**: Keep `plugins/bitwise-embedded-docs/.claude-plugin/plugin.json` version in sync with `pyproject.toml` version.

### Adding a New MCP Tool

1. Create `mcp_embedded_docs/tools/new_tool.py` with an async function returning markdown
2. Register in `server.py` with `@mcp.tool()` (docstring = tool description)
3. Use lazy imports inside the function to keep server startup fast
4. Optionally add a skill in `plugins/bitwise-embedded-docs/skills/` with a `SKILL.md`

## Database Migrations

```bash
# Create a new migration
docker compose exec backend alembic revision --autogenerate -m "description"
# Apply
docker compose exec backend alembic upgrade head
# Rollback one
docker compose exec backend alembic downgrade -1
```

Migrations run automatically on backend startup. Current: 001 (initial), 002 (admin + invites), 003 (OAuth columns).
