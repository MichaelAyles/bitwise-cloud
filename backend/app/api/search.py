import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ApiKeyAuth, get_api_key_auth, get_current_user
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models.document import Document
from app.models.user import User
from app.schemas.search import (
    RegisterSearchRequest,
    SearchRequest,
    SearchResponse,
    SearchResult,
)

router = APIRouter(prefix="/search", tags=["search"])


async def _get_searchable_docs(
    db: AsyncSession,
    user_id: uuid.UUID,
    requested_ids: list[uuid.UUID] | None = None,
) -> tuple[list[str], dict[str, str]]:
    """Get doc IDs and titles for ready documents belonging to user.
    Returns (doc_id_strings, {doc_id_str: title}).
    """
    query = select(Document.id, Document.title).where(
        Document.user_id == user_id,
        Document.status == "ready",
    )
    if requested_ids:
        query = query.where(Document.id.in_(requested_ids))

    result = await db.execute(query)
    rows = result.fetchall()
    doc_ids = [str(row[0]) for row in rows]
    doc_titles = {str(row[0]): row[1] for row in rows}
    return doc_ids, doc_titles


# --- JWT-authenticated search (for web frontend) ---


@router.post("", response_model=SearchResponse)
@limiter.limit("30/minute")
async def search_docs(
    request: Request,
    body: SearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc_ids, doc_titles = await _get_searchable_docs(db, user.id, body.doc_ids)
    if not doc_ids:
        return SearchResponse(results=[], query=body.query, total=0)

    from app.engine.adapter import search_documents

    index_dir = Path(settings.index_dir) / str(user.id)
    hits = search_documents(
        index_dir, doc_ids, doc_titles, body.query, top_k=body.top_k
    )

    results = [
        SearchResult(
            score=h.score,
            text=h.text,
            document_id=uuid.UUID(h.doc_id),
            document_title=h.document_title,
            page_number=h.page_start,
            section=h.section,
        )
        for h in hits
    ]
    return SearchResponse(results=results, query=body.query, total=len(results))


@router.post("/register")
@limiter.limit("30/minute")
async def find_register(
    request: Request,
    body: RegisterSearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc_ids, doc_titles = await _get_searchable_docs(db, user.id, body.doc_ids)
    if not doc_ids:
        raise HTTPException(status_code=404, detail="No searchable documents")

    from app.engine.adapter import find_register_in_documents

    index_dir = Path(settings.index_dir) / str(user.id)
    hit = find_register_in_documents(index_dir, doc_ids, doc_titles, body.name)

    if not hit:
        raise HTTPException(status_code=404, detail=f"Register '{body.name}' not found")

    return {
        "name": body.name,
        "score": hit.score,
        "text": hit.text,
        "document_id": hit.doc_id,
        "document_title": hit.document_title,
        "page_number": hit.page_start,
        "section": hit.section,
        "structured_data": hit.structured_data,
    }


# --- API-key-authenticated search (for MCP / external tools) ---

api_router = APIRouter(prefix="/v1", tags=["api"])


@api_router.post("/search", response_model=SearchResponse)
@limiter.limit("60/minute")
async def api_search_docs(
    request: Request,
    body: SearchRequest,
    auth: ApiKeyAuth = Depends(get_api_key_auth),
    db: AsyncSession = Depends(get_db),
):
    # Intersect requested doc_ids with allowed doc_ids
    allowed = auth.allowed_doc_ids
    if body.doc_ids:
        effective_ids = [d for d in body.doc_ids if d in allowed]
    elif allowed:
        effective_ids = allowed
    else:
        # No document restrictions — search all ready docs
        effective_ids = None

    doc_ids, doc_titles = await _get_searchable_docs(db, auth.user.id, effective_ids)
    if not doc_ids:
        return SearchResponse(results=[], query=body.query, total=0)

    from app.engine.adapter import search_documents

    index_dir = Path(settings.index_dir) / str(auth.user.id)
    hits = search_documents(
        index_dir, doc_ids, doc_titles, body.query, top_k=body.top_k
    )

    results = [
        SearchResult(
            score=h.score,
            text=h.text,
            document_id=uuid.UUID(h.doc_id),
            document_title=h.document_title,
            page_number=h.page_start,
            section=h.section,
        )
        for h in hits
    ]
    return SearchResponse(results=results, query=body.query, total=len(results))


@api_router.post("/register")
@limiter.limit("60/minute")
async def api_find_register(
    request: Request,
    body: RegisterSearchRequest,
    auth: ApiKeyAuth = Depends(get_api_key_auth),
    db: AsyncSession = Depends(get_db),
):
    allowed = auth.allowed_doc_ids
    if body.doc_ids:
        effective_ids = [d for d in body.doc_ids if d in allowed]
    elif allowed:
        effective_ids = allowed
    else:
        effective_ids = None

    doc_ids, doc_titles = await _get_searchable_docs(db, auth.user.id, effective_ids)
    if not doc_ids:
        raise HTTPException(status_code=404, detail="No searchable documents")

    from app.engine.adapter import find_register_in_documents

    index_dir = Path(settings.index_dir) / str(auth.user.id)
    hit = find_register_in_documents(index_dir, doc_ids, doc_titles, body.name)

    if not hit:
        raise HTTPException(status_code=404, detail=f"Register '{body.name}' not found")

    return {
        "name": body.name,
        "score": hit.score,
        "text": hit.text,
        "document_id": hit.doc_id,
        "document_title": hit.document_title,
        "page_number": hit.page_start,
        "section": hit.section,
        "structured_data": hit.structured_data,
    }
