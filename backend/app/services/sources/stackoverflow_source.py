"""
Stack Exchange Search Source - Programming Q&A from Stack Overflow and network
Uses Stack Exchange API v2.3 (no authentication required for basic searches)
"""
import requests
from typing import List, Optional
from .base_source import BaseSource, SearchResult


class StackExchangeSource(BaseSource):
    """Search Stack Exchange network (Stack Overflow, etc.) for technical Q&A"""
    
    def __init__(self):
        self.base_url = "https://api.stackexchange.com/2.3"
        self.headers = {
            'User-Agent': 'Scoolish-AI-Platform/1.0 (Educational; https://scoolish.com)'
        }
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        Search Stack Exchange network
        
        Args:
            query: Search query
            limit: Maximum number of results (default 10)
        
        Returns:
            List of SearchResult objects
        """
        try:
            url = f"{self.base_url}/search/advanced"
            params = {
                'q': query,
                'pagesize': min(limit, 100),
                'order': 'desc',
                'sort': 'relevance',
                'site': 'stackoverflow',  # Can be expanded to other sites
                'filter': 'withbody'  # Include question body
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            if 'items' in data:
                for item in data['items']:
                    title = item.get('title', 'Untitled Question')
                    question_id = item.get('question_id', '')
                    link = item.get('link', '')
                    body = item.get('body', '')
                    score = item.get('score', 0)
                    answer_count = item.get('answer_count', 0)
                    is_answered = item.get('is_answered', False)
                    tags = item.get('tags', [])
                    view_count = item.get('view_count', 0)
                    
                    # Create snippet from body (strip HTML)
                    import re
                    snippet = re.sub(r'<[^>]+>', '', body)[:250] if body else f"{answer_count} answers, {view_count} views"
                    
                    # Confidence based on score, answers, and acceptance
                    confidence = 0.5
                    if is_answered:
                        confidence += 0.2
                    if score > 0:
                        confidence += min(score / 50, 0.2)
                    if answer_count > 0:
                        confidence += min(answer_count / 10, 0.1)
                    
                    results.append(SearchResult(
                        title=title,
                        url=link,
                        snippet=snippet,
                        domain='stackoverflow.com',
                        source='Stack Overflow',
                        source_icon='💻',
                        confidence=min(confidence, 1.0),
                        metadata={
                            'score': score,
                            'answer_count': answer_count,
                            'is_answered': is_answered,
                            'tags': tags,
                            'view_count': view_count,
                            'question_id': question_id
                        }
                    ))
            
            return results[:limit]
            
        except requests.RequestException as e:
            print(f"[StackExchangeSource] Search error: {str(e)}")
            return []
        except Exception as e:
            print(f"[StackExchangeSource] Unexpected error: {str(e)}")
            return []
    
    def is_available(self) -> bool:
        """Check if Stack Exchange API is accessible"""
        try:
            response = requests.get(
                f"{self.base_url}/questions?site=stackoverflow&pagesize=1",
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        except:
            return True  # Assume available
    
    def get_metadata(self) -> dict:
        """Return source metadata"""
        return {
            'name': 'stackoverflow',
            'display_name': 'Stack Overflow',
            'description': 'Programming Q&A and technical solutions',
            'icon': '💻',
            'is_free': True,
            'requires_key': False,
            'enabled': True,
            'rate_limit': '10,000 requests/day (no key), 300 requests/minute (with key)',
            'best_for': ['programming', 'debugging', 'technical questions', 'code solutions']
        }
