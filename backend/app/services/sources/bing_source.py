"""
Bing Search API Source (Existing implementation)
Requires Azure subscription and API key
"""
import os
import requests
from typing import List
from urllib.parse import urlparse
from app.services.sources.base_source import BaseSource, SearchResult


class BingSource(BaseSource):
    """Bing Search API (Microsoft Azure)"""
    
    def __init__(self):
        super().__init__()
        self.name = 'bing'
        self.icon = '🔎'
        self.description = 'Bing Search - Microsoft (requires API key)'
        self.is_free = False
        self.requires_key = True
        self.rate_limit = '3-7 queries/sec (varies by tier)'
        
        # Support multiple keys via BING_SEARCH_API_KEYS or single key
        keys_env = os.getenv('BING_SEARCH_API_KEYS') or os.getenv('BING_SEARCH_API_KEY') or os.getenv('BING_V7_KEY') or ''
        self.api_keys = [k.strip() for k in keys_env.split(',') if k.strip()]
        
        # Endpoint configuration
        raw_endpoint = os.getenv('BING_SEARCH_ENDPOINT', 'https://api.bing.microsoft.com')
        self.endpoint = self._ensure_bing_endpoint(raw_endpoint)
        self.market = os.getenv('BING_SEARCH_MARKET', 'en-US')
    
    def _ensure_bing_endpoint(self, raw: str) -> str:
        """Normalize endpoint to v7.0/search"""
        raw = (raw or "").strip().rstrip("/")
        if not raw:
            return "https://api.bing.microsoft.com/v7.0/search"
        if raw.endswith("/v7.0/search"):
            return raw
        return raw + "/v7.0/search"
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search using Bing API"""
        if not self.api_keys:
            raise Exception('Bing API key not configured')
        
        results = []
        
        # Clamp limit to Bing's max of 50
        limit = max(1, min(limit, 50))
        
        params = {
            'q': query,
            'mkt': self.market,
            'count': str(limit),
            'offset': '0',
            'responseFilter': 'Webpages',
            'safeSearch': 'Moderate',
            'textDecorations': 'false',
            'setLang': self.market.split('-')[0] if '-' in self.market else self.market,
        }
        
        last_err = None
        
        # Try keys in order; rotate on errors
        for api_key in self.api_keys:
            try:
                headers = {'Ocp-Apim-Subscription-Key': api_key}
                response = requests.get(self.endpoint, headers=headers, params=params, timeout=15)
                
                # Rotate on auth/quota/server issues
                if response.status_code in (401, 403, 429, 500, 502, 503, 504):
                    last_err = f"HTTP {response.status_code}"
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                # Parse web results
                web_values = ((data.get('webPages') or {}).get('value')) or []
                for i, item in enumerate(web_values):
                    url = item.get('url', '')
                    try:
                        domain = urlparse(url).netloc
                    except Exception:
                        domain = ''
                    
                    results.append(SearchResult(
                        title=item.get('name', ''),
                        snippet=item.get('snippet', ''),
                        url=url,
                        domain=domain,
                        source='bing',
                        source_icon=self.icon,
                        confidence=1.0 - (i * 0.05),
                        metadata={
                            'type': 'web_search',
                            'display_url': item.get('displayUrl', '')
                        }
                    ))
                
                # If no web results, try news
                if not results:
                    news_values = ((data.get('news') or {}).get('value')) or []
                    for i, item in enumerate(news_values):
                        url = item.get('url', '')
                        try:
                            domain = urlparse(url).netloc
                        except Exception:
                            domain = ''
                        
                        results.append(SearchResult(
                            title=item.get('name', ''),
                            snippet=item.get('description', ''),
                            url=url,
                            domain=domain,
                            source='bing',
                            source_icon=self.icon,
                            confidence=0.9 - (i * 0.05),
                            metadata={
                                'type': 'news',
                                'provider': item.get('provider', [{}])[0].get('name', '') if item.get('provider') else ''
                            }
                        ))
                
                return results
                
            except Exception as e:
                last_err = str(e)
                continue
        
        # If all keys failed
        raise Exception(f'Bing search failed: {last_err or "All API keys failed"}')
    
    def is_available(self) -> bool:
        """Check if Bing API key is configured"""
        return len(self.api_keys) > 0
