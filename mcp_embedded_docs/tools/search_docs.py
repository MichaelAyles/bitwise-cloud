"""Search documentation tool."""

from typing import Optional
from ..retrieval.hybrid_search import HybridSearch
from ..retrieval.formatter import ResultFormatter
from ..config import Config

_cached_search: Optional[HybridSearch] = None
_cached_config_hash: Optional[str] = None


def _get_search(config: Config) -> HybridSearch:
    """Get or create a cached HybridSearch instance.

    Reuses the existing instance if the config hasn't changed,
    avoiding expensive model reloads on every call.
    """
    global _cached_search, _cached_config_hash
    config_hash = str(config.index.directory)
    if _cached_search is None or _cached_config_hash != config_hash:
        if _cached_search is not None:
            _cached_search.close()
        _cached_search = HybridSearch(config)
        _cached_config_hash = config_hash
    return _cached_search


async def search_docs(
    query: str,
    top_k: int = 5,
    doc_filter: Optional[str] = None,
    config: Optional[Config] = None
) -> str:
    """Search documentation using hybrid search.

    Args:
        query: Search query
        top_k: Number of results to return (default: 5)
        doc_filter: Optional document ID to filter results
        config: Configuration object

    Returns:
        Formatted search results as markdown
    """
    if config is None:
        config = Config.load()

    search = _get_search(config)

    results = search.search(query, top_k, doc_filter)
    formatted = ResultFormatter.format_results(results, top_k)
    return formatted
