"""
Wikipedia Search Source - MediaWiki REST API
Free, no API key required
"""
import requests
from typing import List
from app.services.sources.base_source import BaseSource, SearchResult


class WikipediaSource(BaseSource):
    """Wikipedia search using MediaWiki API"""
    
    def __init__(self):
        super().__init__()
        self.name = 'wikipedia'
        self.icon = '📚'
        self.description = 'Wikipedia - Free encyclopedia'
        self.is_free = True
        self.requires_key = False
        self.base_url = 'https://en.wikipedia.org'
        self.rate_limit = '200 req/s'
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search Wikipedia articles"""
        results = []
        
        try:
            # Step 1: Search for pages
            search_url = f'{self.base_url}/w/api.php'
            search_params = {
                'action': 'opensearch',
                'search': query,
                'limit': limit,
                'namespace': 0,
                'format': 'json'
            }
            
            headers = {
                'User-Agent': 'Scoolish-AI-Platform/1.0 (Educational; https://scoolish.com)'
            }
            
            response = requests.get(search_url, params=search_params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # OpenSearch returns: [query, [titles], [descriptions], [urls]]
            if len(data) >= 4:
                titles = data[1]
                descriptions = data[2]
                urls = data[3]
                
                for i in range(min(len(titles), limit)):
                    results.append(SearchResult(
                        title=titles[i],
                        snippet=descriptions[i] if i < len(descriptions) else '',
                        url=urls[i] if i < len(urls) else f'{self.base_url}/wiki/{titles[i].replace(" ", "_")}',
                        domain='en.wikipedia.org',
                        source='wikipedia',
                        source_icon=self.icon,
                        confidence=1.0 - (i * 0.05),  # Decrease confidence with position
                        metadata={
                            'type': 'wikipedia_article',
                            'language': 'en'
                        }
                    ))
            
        except Exception as e:
            # Re-raise to be caught by manager
            raise Exception(f'Wikipedia search failed: {str(e)}')
        
        return results
    
    def is_available(self) -> bool:
        """Check if Wikipedia API is accessible"""
        # Wikipedia is always available, check at search time
        return True
