"""
Search Source Manager - Orchestrates multiple search sources
"""
import os
from typing import List, Dict, Optional, Any
from app.services.sources import (
    BaseSource,
    SearchResult,
    WikipediaSource,
    DuckDuckGoSource,
    BraveSource,
    ArxivSource,
    OpenLibrarySource,
    GitHubSource,
    BingSource,
    GoogleBooksSource,
    StackExchangeSource,
    WikimediaCommonsSource,
    ProjectGutenbergSource,
)


class SearchSourceManager:
    """Manages multiple search sources with unified interface"""
    
    def __init__(self):
        # Initialize all sources
        self.sources: Dict[str, BaseSource] = {
            'wikipedia': WikipediaSource(),
            'duckduckgo': DuckDuckGoSource(),
            'brave': BraveSource(),
            'arxiv': ArxivSource(),
            'openlibrary': OpenLibrarySource(),
            'github': GitHubSource(),
            'bing': BingSource(),
            'google_books': GoogleBooksSource(),
            'stackoverflow': StackExchangeSource(),
            'wikimedia_commons': WikimediaCommonsSource(),
            'gutenberg': ProjectGutenbergSource(),
        }
        
        # Filter to only available sources
        self._filter_available_sources()
    
    def _filter_available_sources(self):
        """Remove sources that aren't available or enabled"""
        available = {}
        for name, source in self.sources.items():
            try:
                if source.is_available():
                    available[name] = source
                else:
                    print(f"[SearchSourceManager] Source '{name}' is not available")
            except Exception as e:
                print(f"[SearchSourceManager] Error checking availability for '{name}': {str(e)}")
        self.sources = available
        print(f"[SearchSourceManager] Loaded {len(self.sources)} sources: {list(self.sources.keys())}")
    
    def get_available_sources(self) -> List[Dict[str, Any]]:
        """Get list of all available sources with metadata"""
        return [source.get_metadata() for source in self.sources.values()]
    
    def get_source(self, name: str) -> Optional[BaseSource]:
        """Get a specific source by name"""
        return self.sources.get(name.lower())
    
    def search(
        self,
        query: str,
        source: str = 'all',
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Execute search across one or more sources
        
        Args:
            query: Search query string
            source: Source name or 'all' for all sources
            limit: Maximum results per source
            
        Returns:
            Dict with results, errors, and metadata
        """
        results = []
        errors = []
        sources_searched = []
        
        # Determine which sources to search
        if source == 'all':
            sources_to_search = list(self.sources.items())
        elif source in self.sources:
            sources_to_search = [(source, self.sources[source])]
        else:
            return {
                'results': [],
                'errors': [{'source': source, 'error': 'Source not found or not available'}],
                'sources_searched': [],
                'total_results': 0
            }
        
        # Search each source
        for source_name, source_obj in sources_to_search:
            try:
                source_results = source_obj.search(query, limit=limit)
                results.extend(source_results)
                sources_searched.append(source_name)
            except Exception as e:
                errors.append({
                    'source': source_name,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
        
        # Sort results by confidence (if available)
        results.sort(key=lambda r: r.confidence, reverse=True)
        
        return {
            'results': [r.to_dict() for r in results],
            'errors': errors,
            'sources_searched': sources_searched,
            'total_results': len(results)
        }
    
    def test_source(self, name: str) -> Dict[str, Any]:
        """Test a specific source"""
        source = self.get_source(name)
        if not source:
            return {
                'status': 'error',
                'available': False,
                'message': f'Source {name} not found'
            }
        return source.test_connection()
    
    def test_all_sources(self) -> Dict[str, Dict[str, Any]]:
        """Test all sources and return status"""
        results = {}
        for name, source in self.sources.items():
            results[name] = source.test_connection()
        return results
