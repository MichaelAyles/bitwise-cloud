"""Streamable HTTP MCP server endpoint for bitwise-cloud.

Authenticated via API key, exposes search_docs and find_register tools
scoped to the documents the API key has access to.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from app.config import settings

mcp = FastMCP(
    "BitWise Cloud",
    stateless_http=True,
    streamable_http_path="/",
)


def _get_sync_session():
    """Get a sync SQLAlchemy session for use in MCP tool handlers."""
    import os

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = os.environ.get("SYNC_DATABASE_URL", "")
    if not db_url:
        db_url = os.environ.get("DATABASE_URL", "").replace(
            "postgresql+asyncpg://", "postgresql://"
        )
    engine = create_engine(db_url)
    return sessionmaker(bind=engine)()


def _resolve_api_key(raw_key: str) -> tuple[uuid.UUID, list[uuid.UUID]]:
    """Validate API key and return (user_id, allowed_doc_ids).

    Raises ValueError if invalid/expired.
    """
    from app.models.api_key import ApiKey, ApiKeyDocument

    db = _get_sync_session()
    try:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = db.query(ApiKey).filter(
            ApiKey.key_hash == key_hash, ApiKey.is_active == True
        ).first()

        if not api_key:
            raise ValueError("Invalid API key")
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            raise ValueError("API key expired")

        doc_links = db.query(ApiKeyDocument.document_id).filter(
            ApiKeyDocument.api_key_id == api_key.id
        ).all()
        allowed_doc_ids = [row[0] for row in doc_links]

        # Update usage
        api_key.last_used_at = datetime.now(timezone.utc)
        api_key.request_count += 1
        db.commit()

        return api_key.user_id, allowed_doc_ids
    finally:
        db.close()


def _get_ready_docs(
    user_id: uuid.UUID, allowed_doc_ids: list[uuid.UUID]
) -> tuple[list[str], dict[str, str]]:
    """Get ready doc IDs and titles for user, filtered by allowed list."""
    from app.models.document import Document

    db = _get_sync_session()
    try:
        query = db.query(Document.id, Document.title).filter(
            Document.user_id == user_id, Document.status == "ready"
        )
        if allowed_doc_ids:
            query = query.filter(Document.id.in_(allowed_doc_ids))
        rows = query.all()
        doc_ids = [str(row[0]) for row in rows]
        doc_titles = {str(row[0]): row[1] for row in rows}
        return doc_ids, doc_titles
    finally:
        db.close()


@mcp.tool()
def search_docs(
    query: str,
    top_k: int = 5,
    api_key: str = "",
) -> str:
    """Search embedded systems documentation using hybrid keyword + semantic search.

    Args:
        query: Search query (natural language or keywords)
        top_k: Number of results to return (default 5)
        api_key: Your BitWise Cloud API key (required)
    """
    if not api_key:
        return "Error: api_key parameter is required"

    try:
        user_id, allowed_doc_ids = _resolve_api_key(api_key)
    except ValueError as e:
        return f"Error: {e}"

    doc_ids, doc_titles = _get_ready_docs(user_id, allowed_doc_ids)
    if not doc_ids:
        return "No searchable documents found for this API key."

    from app.engine.adapter import search_documents

    index_dir = Path(settings.index_dir) / str(user_id)
    hits = search_documents(index_dir, doc_ids, doc_titles, query, top_k=top_k)

    if not hits:
        return f"No results found for: {query}"

    lines = [f"## Search Results for: {query}\n"]
    for i, h in enumerate(hits, 1):
        lines.append(f"### {i}. {h.document_title}")
        if h.section:
            lines.append(f"**Section:** {h.section}")
        lines.append(f"**Page:** {h.page_start} | **Score:** {h.score:.2f}")
        lines.append(f"\n{h.text[:2000]}\n")
        lines.append("---\n")

    return "\n".join(lines)


@mcp.tool()
def find_register(
    name: str,
    peripheral: str | None = None,
    api_key: str = "",
) -> str:
    """Find a specific hardware register by name in indexed documentation.

    Args:
        name: Register name (e.g. 'CANSTAT', 'CNF1')
        peripheral: Optional peripheral name to filter results
        api_key: Your BitWise Cloud API key (required)
    """
    if not api_key:
        return "Error: api_key parameter is required"

    try:
        user_id, allowed_doc_ids = _resolve_api_key(api_key)
    except ValueError as e:
        return f"Error: {e}"

    doc_ids, doc_titles = _get_ready_docs(user_id, allowed_doc_ids)
    if not doc_ids:
        return "No searchable documents found for this API key."

    from app.engine.adapter import find_register_in_documents

    index_dir = Path(settings.index_dir) / str(user_id)
    hit = find_register_in_documents(
        index_dir, doc_ids, doc_titles, name, peripheral
    )

    if not hit:
        return f"Register '{name}' not found."

    lines = [f"## Register: {name}\n"]
    lines.append(f"**Document:** {hit.document_title}")
    lines.append(f"**Page:** {hit.page_start}")
    if hit.section:
        lines.append(f"**Section:** {hit.section}")
    lines.append(f"\n{hit.text[:3000]}\n")

    if hit.structured_data and "registers" in hit.structured_data:
        import json

        lines.append("\n### Structured Data\n")
        lines.append(f"```json\n{json.dumps(hit.structured_data, indent=2)}\n```")

    return "\n".join(lines)
