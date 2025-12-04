"""
GitHub Search Source - Code repositories
Free tier: 60 req/hr (unauthenticated), 5000 req/hr (authenticated)
"""
import os
import requests
from typing import List
from app.services.sources.base_source import BaseSource, SearchResult


class GitHubSource(BaseSource):
    """GitHub repository and code search"""
    
    def __init__(self):
        super().__init__()
        self.name = 'github'
        self.icon = '💻'
        self.description = 'GitHub - Code repositories'
        self.is_free = True
        self.requires_key = False  # Optional token for higher limits
        self.token = os.getenv('GITHUB_TOKEN', '')
        self.base_url = 'https://api.github.com'
        self.rate_limit = '60/hr (5000/hr with token)'
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search GitHub repositories"""
        results = []
        
        try:
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Scoolish-WebDock'
            }
            
            if self.token:
                headers['Authorization'] = f'token {self.token}'
            
            search_url = f'{self.base_url}/search/repositories'
            params = {
                'q': query,
                'per_page': min(limit, 30),
                'sort': 'stars',
                'order': 'desc'
            }
            
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            items = data.get('items', [])
            
            for i, repo in enumerate(items[:limit]):
                # Build snippet with stats
                snippet_parts = []
                if repo.get('description'):
                    snippet_parts.append(repo['description'])
                
                stats = []
                if repo.get('stargazers_count'):
                    stats.append(f"⭐ {repo['stargazers_count']}")
                if repo.get('forks_count'):
                    stats.append(f"🔀 {repo['forks_count']}")
                if repo.get('language'):
                    stats.append(repo['language'])
                
                if stats:
                    snippet_parts.append(' • '.join(stats))
                
                snippet = ' | '.join(snippet_parts)
                
                results.append(SearchResult(
                    title=repo.get('full_name', repo.get('name', '')),
                    snippet=snippet,
                    url=repo.get('html_url', ''),
                    domain='github.com',
                    source='github',
                    source_icon=self.icon,
                    confidence=1.0 - (i * 0.05),
                    metadata={
                        'type': 'repository',
                        'owner': repo.get('owner', {}).get('login', ''),
                        'stars': repo.get('stargazers_count', 0),
                        'forks': repo.get('forks_count', 0),
                        'language': repo.get('language', ''),
                        'topics': repo.get('topics', []),
                        'created_at': repo.get('created_at', ''),
                        'updated_at': repo.get('updated_at', ''),
                        'license': repo.get('license', {}).get('name', '') if repo.get('license') else None
                    }
                ))
            
        except Exception as e:
            raise Exception(f'GitHub search failed: {str(e)}')
        
        return results
    
    def is_available(self) -> bool:
        """Check if GitHub API is accessible"""
        # GitHub is always available (public API), check at search time
        return True
