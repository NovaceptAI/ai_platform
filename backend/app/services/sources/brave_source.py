"""
Brave Search API Source
Free tier: 2,000 queries/month
"""
import os
import requests
from typing import List
from app.services.sources.base_source import BaseSource, SearchResult


class BraveSource(BaseSource):
    """Brave Search API"""
    
    def __init__(self):
        super().__init__()
        self.name = 'brave'
        self.icon = '🦁'
        self.description = 'Brave Search - Privacy-focused (2K free/month)'
        self.is_free = True  # Free tier available
        self.requires_key = True
        self.api_key = os.getenv('BRAVE_API_KEY', '')
        self.base_url = 'https://api.search.brave.com/res/v1/web/search'
        self.rate_limit = '1 req/s (free tier)'
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search using Brave Search API"""
        if not self.api_key:
            raise Exception('Brave API key not configured')
        
        results = []
        
        try:
            headers = {
                'Accept': 'application/json',
                'X-Subscription-Token': self.api_key
            }
            
            params = {
                'q': query,
                'count': min(limit, 20),  # Max 20 per request
                'search_lang': 'en',
                'safesearch': 'moderate'
            }
            
            response = requests.get(self.base_url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Parse web results
            web_results = data.get('web', {}).get('results', [])
            for i, result in enumerate(web_results[:limit]):
                results.append(SearchResult(
                    title=result.get('title', ''),
                    snippet=result.get('description', ''),
                    url=result.get('url', ''),
                    domain='',  # Will be auto-extracted
                    source='brave',
                    source_icon=self.icon,
                    confidence=1.0 - (i * 0.05),
                    metadata={
                        'type': 'web_search',
                        'age': result.get('age', ''),
                        'language': result.get('language', '')
                    }
                ))
            
        except Exception as e:
            raise Exception(f'Brave search failed: {str(e)}')
        
        return results
    
    def is_available(self) -> bool:
        """Check if Brave API key is configured and valid"""
        return bool(self.api_key)
