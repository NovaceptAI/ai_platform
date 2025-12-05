"""
Reddit Search Source - Community discussions and content
Uses Reddit OAuth API with client credentials flow
"""
import os
import requests
from typing import List, Optional
from requests.auth import HTTPBasicAuth
from .base_source import BaseSource, SearchResult


class RedditSource(BaseSource):
    """Search Reddit for discussions, opinions, and community content"""
    
    def __init__(self):
        self.base_url = "https://oauth.reddit.com"
        self.token_url = "https://www.reddit.com/api/v1/access_token"
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.access_token = None
        self.headers = {
            'User-Agent': 'Scoolish-AI-Platform/1.0 (Educational; https://scoolish.com)'
        }
    
    def _get_access_token(self) -> Optional[str]:
        """Get OAuth access token using client credentials"""
        if not self.client_id or not self.client_secret:
            print("[RedditSource] Missing OAuth credentials")
            return None
        
        try:
            response = requests.post(
                self.token_url,
                auth=HTTPBasicAuth(self.client_id, self.client_secret),
                data={'grant_type': 'client_credentials'},
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            token_data = response.json()
            return token_data.get('access_token')
        except Exception as e:
            print(f"[RedditSource] Token error: {str(e)}")
            return None
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        Search Reddit posts and comments
        
        Args:
            query: Search query
            limit: Maximum number of results (default 10)
        
        Returns:
            List of SearchResult objects
        """
        try:
            # Get access token if not already cached
            if not self.access_token:
                self.access_token = self._get_access_token()
            
            if not self.access_token:
                print("[RedditSource] Cannot search without access token")
                return []
            
            # Use Reddit's OAuth search endpoint
            url = f"{self.base_url}/search"
            params = {
                'q': query,
                'limit': min(limit, 25),  # Reddit max is 25 per request
                'sort': 'relevance',
                'type': 'link'  # Posts only, not comments
            }
            
            headers = {
                **self.headers,
                'Authorization': f'Bearer {self.access_token}'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            if 'data' in data and 'children' in data['data']:
                for post in data['data']['children']:
                    post_data = post.get('data', {})
                    
                    # Extract post information
                    title = post_data.get('title', '')
                    subreddit = post_data.get('subreddit', '')
                    permalink = post_data.get('permalink', '')
                    selftext = post_data.get('selftext', '')
                    url = post_data.get('url', '')
                    score = post_data.get('score', 0)
                    num_comments = post_data.get('num_comments', 0)
                    
                    # Create snippet from selftext or use placeholder
                    snippet = selftext[:200] if selftext else f"Discussion in r/{subreddit} with {num_comments} comments"
                    
                    # Full URL (use reddit.com, not oauth subdomain)
                    full_url = f"https://www.reddit.com{permalink}"
                    
                    # Confidence based on score and comments
                    confidence = min(0.5 + (score / 1000) + (num_comments / 100), 1.0)
                    
                    results.append(SearchResult(
                        title=title,
                        url=full_url,
                        snippet=snippet,
                        domain='reddit.com',
                        source='Reddit',
                        source_icon='🗨️',
                        confidence=confidence,
                        metadata={
                            'subreddit': subreddit,
                            'score': score,
                            'num_comments': num_comments,
                            'external_url': url if url != full_url else None
                        }
                    ))
            
            return results[:limit]
            
        except requests.RequestException as e:
            print(f"[RedditSource] Search error: {str(e)}")
            return []
        except Exception as e:
            print(f"[RedditSource] Unexpected error: {str(e)}")
            return []
    
    def is_available(self) -> bool:
        """Check if Reddit OAuth credentials are configured"""
        return bool(self.client_id and self.client_secret)
    
    def get_metadata(self) -> dict:
        """Return source metadata"""
        return {
            'name': 'reddit',
            'display_name': 'Reddit',
            'description': 'Community discussions and user-generated content',
            'icon': '🗨️',
            'is_free': True,
            'requires_key': False,
            'enabled': True,
            'rate_limit': 'No strict limit, be respectful',
            'best_for': ['discussions', 'opinions', 'community knowledge', 'troubleshooting']
        }
