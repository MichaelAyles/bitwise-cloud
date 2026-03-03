"""MCP server for the Bitwise Cloud client."""

from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("bitwise-cloud")


def _api_error(e: httpx.HTTPStatusError) -> str:
    """Format an API error into a user-friendly message."""
    status = e.response.status_code
    if status == 401:
        return "Authentication failed — check your API key."
    try:
        detail = e.response.json().get("detail", e.response.text)
    except Exception:
        detail = e.response.text
    if status == 404:
        return detail
    if status == 409:
        return detail
    return f"API error ({status}): {detail}"


def _conn_error() -> str:
    return "Could not connect to Bitwise Cloud. Check your network and API URL."


@mcp.tool()
async def set_api_key(key: str) -> str:
    """Save a Bitwise Cloud API key to local config.

    Get your API key from https://bitwise.mikeayles.com/api-keys

    Args:
        key: API key (starts with bw_)
    """
    if not key.startswith("bw_") or len(key) < 10:
        return "Invalid API key format. Keys start with 'bw_' and are at least 10 characters."

    from .config import save_api_key

    save_api_key(key)
    return f"API key saved (prefix: {key[:6]}...)"


@mcp.tool()
async def list_docs(directory: str = ".") -> str:
    """List local PDF files and compare with cloud-indexed documents.

    Scans for PDFs recursively, computes file hashes, and compares against
    the Bitwise Cloud index to show which files are indexed, which are
    local-only, and which exist only in the cloud.

    Args:
        directory: Directory to scan for PDFs (default: current directory)
    """
    from .client import BitwiseClient

    client = BitwiseClient()

    # Scan local PDFs
    scan_dir = Path(directory).resolve()
    local_pdfs: dict[str, Path] = {}
    for pdf in scan_dir.rglob("*.pdf"):
        if any(p.startswith(".") for p in pdf.relative_to(scan_dir).parts):
            continue
        file_hash = client.hash_file(pdf)
        local_pdfs[file_hash] = pdf

    # Fetch cloud documents
    try:
        cloud_docs = await client.list_documents()
    except httpx.HTTPStatusError as e:
        cloud_docs = []
        cloud_error = _api_error(e)
    except httpx.TransportError:
        cloud_docs = []
        cloud_error = _conn_error()
    else:
        cloud_error = None

    cloud_by_hash: dict[str, dict] = {}
    for doc in cloud_docs:
        cloud_by_hash[doc["file_hash"]] = doc

    # Compare
    indexed = []
    local_only = []
    cloud_only = []

    for h, path in local_pdfs.items():
        if h in cloud_by_hash:
            doc = cloud_by_hash[h]
            indexed.append(
                f"- **{path.name}** → {doc['title']} ({doc['status']}, "
                f"{doc['chunk_count']} chunks, {doc['register_count']} registers)"
            )
        else:
            local_only.append(f"- {path.name}")

    for h, doc in cloud_by_hash.items():
        if h not in local_pdfs:
            cloud_only.append(f"- {doc['title']} ({doc['filename']}, {doc['status']})")

    lines = []
    if cloud_error:
        lines.append(f"**Cloud error**: {cloud_error}\n")
    if indexed:
        lines.append("## Cloud-Indexed")
        lines.extend(indexed)
    if local_only:
        lines.append("\n## Local Only (not uploaded)")
        lines.extend(local_only)
    if cloud_only:
        lines.append("\n## Cloud Only (not found locally)")
        lines.extend(cloud_only)

    if not lines:
        return "No PDFs found locally and no documents in the cloud."

    return "\n".join(lines)


@mcp.tool()
async def upload_doc(doc_path: str, title: str | None = None) -> str:
    """Upload a PDF document to Bitwise Cloud for indexing.

    The document will be queued for ingestion. Use check_progress to
    monitor the indexing status.

    Args:
        doc_path: Path to the PDF file to upload
        title: Optional title for the document (defaults to filename)
    """
    from .client import BitwiseClient

    path = Path(doc_path).resolve()
    if not path.exists():
        return f"File not found: {path}"
    if not path.suffix.lower() == ".pdf":
        return "Only PDF files are supported."

    client = BitwiseClient()
    try:
        doc = await client.upload_document(path, title)
    except httpx.HTTPStatusError as e:
        return _api_error(e)
    except httpx.TransportError:
        return _conn_error()

    return (
        f"Uploaded **{doc['title']}** (id: `{doc['id']}`)\n"
        f"Status: {doc['status']}\n\n"
        f"Use `check_progress(\"{doc['id']}\")` to monitor ingestion."
    )


@mcp.tool()
async def check_progress(doc_id: str) -> str:
    """Check the ingestion progress of a document.

    Args:
        doc_id: Document ID (from upload_doc or list_docs)
    """
    from .client import BitwiseClient

    client = BitwiseClient()
    try:
        progress = await client.get_progress(doc_id)
    except httpx.HTTPStatusError as e:
        return _api_error(e)
    except httpx.TransportError:
        return _conn_error()

    msg = progress.get("progress_message") or ""
    return (
        f"Status: **{progress['status']}**\n"
        f"Progress: {progress['progress_percent']}%"
        + (f"\n{msg}" if msg else "")
    )


@mcp.tool()
async def search_docs(
    query: str,
    top_k: int = 5,
    doc_filter: str | None = None,
) -> str:
    """Search embedded systems documentation using hybrid keyword + semantic search.

    Returns relevant sections and register definitions from cloud-indexed documents.

    Args:
        query: Search query (natural language or keywords)
        top_k: Number of results to return
        doc_filter: Optional comma-separated document IDs to search within
    """
    from .client import BitwiseClient

    client = BitwiseClient()
    doc_ids = [d.strip() for d in doc_filter.split(",")] if doc_filter else None

    try:
        result = await client.search(query, top_k, doc_ids)
    except httpx.HTTPStatusError as e:
        return _api_error(e)
    except httpx.TransportError:
        return _conn_error()

    results = result.get("results", [])
    if not results:
        return f"No results found for: {query}"

    lines = [f"## Search: {query}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"### {i}. {r.get('document_title', 'Unknown')}")
        if r.get("section"):
            lines.append(f"*Section: {r['section']}*")
        if r.get("page_number"):
            lines.append(f"*Page {r['page_number']}*")
        lines.append(f"\n{r['text']}\n")

    return "\n".join(lines)


@mcp.tool()
async def find_register(
    name: str,
    peripheral: str | None = None,
) -> str:
    """Find a specific hardware register by name.

    Returns detailed register definition including address, bit fields,
    and descriptions.

    Args:
        name: Register name (e.g. 'MCR', 'CTRL')
        peripheral: Optional peripheral name to narrow the search (e.g. 'FlexCAN0')
    """
    from .client import BitwiseClient

    client = BitwiseClient()
    search_name = f"{peripheral} {name}" if peripheral else name

    try:
        result = await client.find_register(search_name)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Register '{search_name}' not found."
        return _api_error(e)
    except httpx.TransportError:
        return _conn_error()

    lines = [f"## Register: {result.get('name', name)}"]
    if result.get("document_title"):
        lines.append(f"*Source: {result['document_title']}*")
    if result.get("page_number"):
        lines.append(f"*Page {result['page_number']}*")
    if result.get("section"):
        lines.append(f"*Section: {result['section']}*")
    lines.append(f"\n{result['text']}")

    return "\n".join(lines)
