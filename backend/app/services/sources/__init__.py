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
from .google_books_source import GoogleBooksSource
from .stackoverflow_source import StackExchangeSource
from .wikimedia_commons_source import WikimediaCommonsSource
from .gutenberg_source import ProjectGutenbergSource

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
    'GoogleBooksSource',
    'StackExchangeSource',
    'WikimediaCommonsSource',
    'ProjectGutenbergSource',
]
