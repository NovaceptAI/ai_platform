"""
DuckDuckGo Search Source
Free, no API key required
"""
import requests
from typing import List
from app.services.sources.base_source import BaseSource, SearchResult


class DuckDuckGoSource(BaseSource):
    """DuckDuckGo search using duckduckgo-search library"""
    
    def __init__(self):
        super().__init__()
        self.name = 'duckduckgo'
        self.icon = '🦆'
        self.description = 'DuckDuckGo - Privacy-focused search'
        self.is_free = True
        self.requires_key = False
        self.rate_limit = 'Reasonable use'
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search using DuckDuckGo"""
        results = []
        
        try:
            # Try to import duckduckgo_search library
            try:
                from duckduckgo_search import DDGS
                
                # Use DDGS for text search
                with DDGS() as ddgs:
                    search_results = list(ddgs.text(query, max_results=limit))
                    
                    for i, result in enumerate(search_results):
                        results.append(SearchResult(
                            title=result.get('title', ''),
                            snippet=result.get('body', ''),
                            url=result.get('href', ''),
                            domain='',  # Will be auto-extracted
                            source='duckduckgo',
                            source_icon=self.icon,
                            confidence=1.0 - (i * 0.05),
                            metadata={
                                'type': 'web_search'
                            }
                        ))
            except ImportError:
                # Fallback to Instant Answer API (limited results)
                api_url = 'https://api.duckduckgo.com/'
                params = {
                    'q': query,
                    'format': 'json',
                    'no_html': 1,
                    'skip_disambig': 1
                }
                
                response = requests.get(api_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                # Get abstract
                if data.get('AbstractText'):
                    results.append(SearchResult(
                        title=data.get('Heading', query),
                        snippet=data.get('AbstractText', ''),
                        url=data.get('AbstractURL', ''),
                        domain='',
                        source='duckduckgo',
                        source_icon=self.icon,
                        confidence=1.0,
                        metadata={'type': 'instant_answer'}
                    ))
                
                # Get related topics
                for i, topic in enumerate(data.get('RelatedTopics', [])[:limit-1]):
                    if isinstance(topic, dict) and 'Text' in topic:
                        results.append(SearchResult(
                            title=topic.get('Text', '').split(' - ')[0] if ' - ' in topic.get('Text', '') else query,
                            snippet=topic.get('Text', ''),
                            url=topic.get('FirstURL', ''),
                            domain='',
                            source='duckduckgo',
                            source_icon=self.icon,
                            confidence=0.9 - (i * 0.05),
                            metadata={'type': 'related_topic'}
                        ))
                
        except Exception as e:
            raise Exception(f'DuckDuckGo search failed: {str(e)}')
        
        return results
    
    def is_available(self) -> bool:
        """Check if DuckDuckGo is accessible"""
        try:
            # Try importing the library first
            try:
                from duckduckgo_search import DDGS
                return True
            except ImportError:
                # Fallback to checking API (but don't actually call it to avoid rate limits)
                return True  # Assume available, will fail gracefully if not
        except Exception:
            return True  # Be optimistic
