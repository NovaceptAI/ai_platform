"""
Search source implementations for WebDock multi-source scraper
"""
from .base_source import BaseSource, SearchResult
from .wikipedia_source import WikipediaSource
from .duckduckgo_source import DuckDuckGoSource
from .brave_source import BraveSource
from .arxiv_source import ArxivSource
from .openlibrary_source import OpenLibrarySource
from .github_source import GitHubSource
from .bing_source import BingSource

__all__ = [
    'BaseSource',
    'SearchResult',
    'WikipediaSource',
    'DuckDuckGoSource',
    'BraveSource',
    'ArxivSource',
    'OpenLibrarySource',
    'GitHubSource',
    'BingSource',
]
