"""Find register tool."""

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


async def find_register(
    name: str,
    peripheral: Optional[str] = None,
    config: Optional[Config] = None
) -> str:
    """Find a specific register by name.

    Args:
        name: Register name to find
        peripheral: Optional peripheral name to filter results
        config: Configuration object

    Returns:
        Formatted register definition as markdown
    """
    if config is None:
        config = Config.load()

    search = _get_search(config)

    result = search.find_register(name, peripheral)

    if not result:
        return f"Register '{name}' not found."

    return ResultFormatter.format_register(result)
