"""Adapter wrapping bitwise-mcp's engine for multi-tenant use.

Provides a shared embedder singleton and parameterized paths per user/document.
"""

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Lazy singleton for the embedder — loaded once, shared across all tenants
_embedder = None
_embedder_lock = threading.Lock()

# Cache for loaded indices to avoid expensive disk I/O
# Maps (path_str) -> Store instance
_vector_store_cache: dict[str, Any] = {}
_metadata_store_cache: dict[str, Any] = {}
_cache_lock = threading.Lock()
MAX_CACHE_SIZE = 100


def get_shared_embedder():
    """Get or create the shared LocalEmbedder instance (thread-safe)."""
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                from mcp_embedded_docs.indexing.embedder import LocalEmbedder

                from app.config import settings

                logger.info("Loading embedding model: %s", settings.embedding_model)
                _embedder = LocalEmbedder(
                    model_name=settings.embedding_model,
                    device="cpu",
                )
                logger.info("Embedding model loaded (dim=%d)", _embedder.dimension)
    return _embedder


def _get_vector_store(path: Path, dimension: int) -> Any:
    path_str = str(path)
    with _cache_lock:
        if path_str in _vector_store_cache:
            return _vector_store_cache[path_str]

        from mcp_embedded_docs.indexing.vector_store import VectorStore

        vs = VectorStore(dimension=dimension)
        vs.load(path)

        # Basic LRU: if cache too big, clear it (simple approach)
        if len(_vector_store_cache) >= MAX_CACHE_SIZE:
            _vector_store_cache.clear()

        _vector_store_cache[path_str] = vs
        return vs


def _get_metadata_store(path: Path) -> Any:
    path_str = str(path)
    with _cache_lock:
        if path_str in _metadata_store_cache:
            return _metadata_store_cache[path_str]

        from mcp_embedded_docs.indexing.metadata_store import MetadataStore

        ms = MetadataStore(path)

        if len(_metadata_store_cache) >= MAX_CACHE_SIZE:
            # Close old connections before clearing
            for store in _metadata_store_cache.values():
                try:
                    store.close()
                except Exception:
                    pass
            _metadata_store_cache.clear()

        _metadata_store_cache[path_str] = ms
        return ms


@dataclass
class IngestionResult:
    page_count: int
    chunk_count: int
    register_count: int


ProgressCallback = Callable[[int, str], None]


class IngestionPipeline:
    """Run the full ingestion pipeline for a single document."""

    def __init__(self, pdf_path: Path, index_dir: Path, doc_id: str):
        self.pdf_path = pdf_path
        self.index_dir = index_dir
        self.doc_id = doc_id

    def run(self, progress_callback: ProgressCallback | None = None) -> IngestionResult:
        from mcp_embedded_docs.config import ChunkingConfig
        from mcp_embedded_docs.indexing.metadata_store import MetadataStore
        from mcp_embedded_docs.indexing.vector_store import VectorStore
        from mcp_embedded_docs.ingestion.chunker import SemanticChunker
        from mcp_embedded_docs.ingestion.pdf_parser import PDFParser
        from mcp_embedded_docs.ingestion.table_detector import TableDetector
        from mcp_embedded_docs.ingestion.table_extractor import TableExtractor

        def _progress(pct: int, msg: str):
            if progress_callback:
                progress_callback(pct, msg)

        # 1. Parse PDF
        _progress(5, "Parsing PDF")
        with PDFParser(self.pdf_path) as parser:
            pages = parser.extract_text_with_layout()
            toc = parser.extract_toc()
            sections = parser.detect_sections(pages, toc)
        page_count = len(pages)
        _progress(15, f"Parsed {page_count} pages, {len(sections)} sections")

        # 2. Detect and extract tables
        _progress(20, "Detecting register tables")
        extractor = TableExtractor(str(self.pdf_path))
        all_tables: list[Any] = []
        table_pages: dict[int, int] = {}

        with TableDetector(str(self.pdf_path)) as detector:
            for page in pages:
                regions = detector.detect_register_tables(page)
                for region in regions:
                    context = detector.detect_table_context(page, region)
                    table = extractor.extract_register_table(region, context)
                    if table:
                        table_pages[len(all_tables)] = region.page_num
                        all_tables.append(table)

        _progress(35, f"Found {len(all_tables)} register tables")

        # 3. Chunk
        _progress(40, "Creating semantic chunks")
        chunking_cfg = ChunkingConfig()
        chunker = SemanticChunker(
            target_size=chunking_cfg.target_size,
            overlap=chunking_cfg.overlap,
            preserve_tables=chunking_cfg.preserve_tables,
        )
        doc_title = self.pdf_path.stem
        chunks = chunker.chunk_document(
            self.doc_id,
            sections,
            all_tables,
            doc_title=doc_title,
            table_pages=table_pages,
        )
        _progress(50, f"Created {len(chunks)} chunks")

        # 4. Embed
        _progress(55, "Generating embeddings")
        embedder = get_shared_embedder()
        chunk_texts = [c.text for c in chunks]
        embeddings = embedder.embed_batch(chunk_texts, show_progress=False)
        _progress(75, "Embeddings complete")

        # 5. Build indices
        _progress(80, "Building search index")
        self.index_dir.mkdir(parents=True, exist_ok=True)

        vector_path = self.index_dir / f"vectors_{self.doc_id}.faiss"
        metadata_path = self.index_dir / f"metadata_{self.doc_id}.db"

        vector_store = VectorStore(dimension=embedder.dimension)
        vector_store.add_vectors(embeddings, [c.id for c in chunks])
        vector_store.save(vector_path)

        metadata_store = MetadataStore(metadata_path)
        metadata_store.add_document(
            doc_id=self.doc_id,
            filename=self.pdf_path.name,
            title=doc_title,
        )
        register_count = 0
        for chunk in chunks:
            metadata_store.add_chunk(
                chunk_id=chunk.id,
                doc_id=chunk.doc_id,
                chunk_type=chunk.chunk_type,
                text=chunk.text,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                structured_data=chunk.structured_data,
                metadata=chunk.metadata,
            )
            if chunk.structured_data and "registers" in chunk.structured_data:
                register_count += len(chunk.structured_data["registers"])

        metadata_store.close()

        # Invalidate cache for this doc since it was updated
        with _cache_lock:
            _vector_store_cache.pop(str(vector_path), None)
            _metadata_store_cache.pop(str(metadata_path), None)

        _progress(100, "Ingestion complete")

        return IngestionResult(
            page_count=page_count,
            chunk_count=len(chunks),
            register_count=register_count,
        )


def remove_document_indices(index_dir: Path, doc_id: str):
    """Remove all index files for a document and clear from cache."""
    vector_path = index_dir / f"vectors_{doc_id}.faiss"
    metadata_path = index_dir / f"metadata_{doc_id}.db"

    with _cache_lock:
        _vector_store_cache.pop(str(vector_path), None)
        ms = _metadata_store_cache.pop(str(metadata_path), None)
        if ms:
            try:
                ms.close()
            except Exception:
                pass

    for pattern in [
        f"vectors_{doc_id}.faiss",
        f"vectors_{doc_id}.ids",
        f"metadata_{doc_id}.db",
    ]:
        path = index_dir / pattern
        if path.exists():
            path.unlink()


@dataclass
class SearchHit:
    chunk_id: str
    score: float
    text: str
    doc_id: str
    document_title: str
    page_start: int
    page_end: int
    section: str | None
    structured_data: dict | None


def search_documents(
    index_dir: Path,
    doc_ids: list[str],
    doc_titles: dict[str, str],
    query: str,
    top_k: int = 10,
) -> list[SearchHit]:
    """Search across multiple per-document indices using hybrid search.

    Uses two-phase scoring: first collect raw scores from all documents,
    then normalize each channel (semantic/keyword) to 0-1 globally before
    combining with weights. This ensures both channels contribute equally.
    """
    import json

    embedder = get_shared_embedder()
    query_vector = embedder.embed_query(query)

    # Phase 1: Collect raw scores from all documents
    raw_semantic: dict[str, float] = {}
    raw_keyword: dict[str, float] = {}
    chunk_doc_map: dict[str, str] = {}

    for doc_id in doc_ids:
        try:
            vector_path = index_dir / f"vectors_{doc_id}.faiss"
            metadata_path = index_dir / f"metadata_{doc_id}.db"

            if not vector_path.exists() or not metadata_path.exists():
                continue

            # Semantic search (cached)
            vs = _get_vector_store(vector_path, embedder.dimension)
            semantic_results = vs.search(query_vector, top_k=top_k * 2)

            for cid, dist in semantic_results:
                score = max(0.0, 1.0 - dist / 2.0)
                raw_semantic[cid] = score
                chunk_doc_map[cid] = doc_id

            # Keyword search (cached)
            ms = _get_metadata_store(metadata_path)
            keyword_results = ms.keyword_search(query, top_k=top_k * 2)

            for cid, score in keyword_results:
                raw_keyword[cid] = score
                chunk_doc_map[cid] = doc_id

        except Exception as e:
            logger.error("Error searching document %s: %s", doc_id, e)
            continue

    # Phase 2: Normalize each channel to 0-1 range globally
    if raw_semantic:
        max_sem = max(raw_semantic.values())
        if max_sem > 0:
            raw_semantic = {k: v / max_sem for k, v in raw_semantic.items()}

    if raw_keyword:
        max_kw = max(raw_keyword.values())
        if max_kw > 0:
            raw_keyword = {k: v / max_kw for k, v in raw_keyword.items()}

    # Phase 3: Combine normalized scores
    all_chunk_ids = set(raw_semantic.keys()) | set(raw_keyword.keys())
    scored_chunks: list[tuple[str, float, str]] = []

    for chunk_id in all_chunk_ids:
        sem = raw_semantic.get(chunk_id, 0.0)
        kw = raw_keyword.get(chunk_id, 0.0)
        combined = 0.6 * sem + 0.4 * kw
        if chunk_id in raw_semantic and chunk_id in raw_keyword:
            combined *= 1.2
        scored_chunks.append((chunk_id, combined, chunk_doc_map[chunk_id]))

    scored_chunks.sort(key=lambda h: h[1], reverse=True)

    # Phase 4: Build result objects for top hits
    all_hits: list[SearchHit] = []

    for chunk_id, score, doc_id in scored_chunks[:top_k]:
        try:
            metadata_path = index_dir / f"metadata_{doc_id}.db"
            ms = _get_metadata_store(metadata_path)
            chunk_data = ms.get_chunk(chunk_id)
            if chunk_data:
                structured = chunk_data.get("structured_data")
                if isinstance(structured, str):
                    try:
                        structured = json.loads(structured)
                    except (json.JSONDecodeError, TypeError):
                        structured = None
                metadata = chunk_data.get("metadata")
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}

                all_hits.append(
                    SearchHit(
                        chunk_id=chunk_id,
                        score=score,
                        text=chunk_data.get("text", ""),
                        doc_id=doc_id,
                        document_title=doc_titles.get(doc_id, ""),
                        page_start=chunk_data.get("page_start", 0),
                        page_end=chunk_data.get("page_end", 0),
                        section=(metadata or {}).get("section_title"),
                        structured_data=structured,
                    )
                )
        except Exception as e:
            logger.error("Error fetching chunk %s: %s", chunk_id, e)
            continue

    return all_hits


def find_register_in_documents(
    index_dir: Path,
    doc_ids: list[str],
    doc_titles: dict[str, str],
    name: str,
    peripheral: str | None = None,
) -> SearchHit | None:
    """Find a register by name across multiple document indices."""
    for doc_id in doc_ids:
        try:
            metadata_path = index_dir / f"metadata_{doc_id}.db"
            if not metadata_path.exists():
                continue

            ms = _get_metadata_store(metadata_path)
            chunk_data = ms.find_register(name, peripheral)

            if chunk_data:
                import json

                structured = chunk_data.get("structured_data")
                if isinstance(structured, str):
                    try:
                        structured = json.loads(structured)
                    except (json.JSONDecodeError, TypeError):
                        structured = None
                metadata = chunk_data.get("metadata")
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}

                return SearchHit(
                    chunk_id=chunk_data["id"],
                    score=1.0,
                    text=chunk_data.get("text", ""),
                    doc_id=doc_id,
                    document_title=doc_titles.get(doc_id, ""),
                    page_start=chunk_data.get("page_start", 0),
                    page_end=chunk_data.get("page_end", 0),
                    section=(metadata or {}).get("section_title"),
                    structured_data=structured,
                )
        except Exception as e:
            logger.error("Error finding register in document %s: %s", doc_id, e)
            continue

    return None
