# Backend — Cloud API Endpoints

## Context

The Bitwise Cloud plugin (a lightweight MCP client) needs API-key-authenticated endpoints for document management. Currently, document endpoints (`/api/documents/*`) only accept JWT auth. Search endpoints already have API key variants at `/api/v1/search` and `/api/v1/register`. We need to add the same for documents.

## New File: `backend/app/api/v1_documents.py`

Three endpoints, all using `get_api_key_auth` from `deps.py`:

### `GET /api/v1/documents`
- List documents belonging to the API key's user
- If API key has scoped documents (`allowed_doc_ids` non-empty), only return those
- If unscoped, return all user documents
- Response: `list[DocumentResponse]`

### `POST /api/v1/documents/upload`
- Accept multipart PDF upload + optional `title` query param
- Reuse validation from `documents.py`: content type, size limit, PDF magic bytes, SHA256 hash, duplicate check
- Save file, create Document record, trigger Celery ingestion task
- Any valid API key can upload (not restricted by `allowed_doc_ids`)
- Response: `DocumentResponse` (201)

### `GET /api/v1/documents/{doc_id}/progress`
- Check ingestion progress for a document
- Validates document belongs to API key's user
- Mirrors logic from `documents.py`: check Celery task state, fall back to document status
- Response: `IngestionProgressResponse`

## Modified: `backend/app/schemas/document.py`

Added `file_hash: str` to `DocumentResponse` between `filename` and `file_size_bytes`.

## Modified: `backend/app/api/router.py`

Imported and registered the new router.

## Hosted Marketplace

### New file: `marketplace-hosted.json`
Plugin list with GitHub source refs for URL-based marketplaces.

### Modified: `Caddyfile`
Added `/plugin` route before the SPA catch-all.

### Modified: `Dockerfile.caddy`
Copies `marketplace-hosted.json` into the image as `/srv/marketplace.json`.
