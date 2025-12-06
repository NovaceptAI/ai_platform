"""
Wikimedia Commons Search Source - Free educational media (images, videos, audio)
Uses Wikimedia Commons API (same as Wikipedia MediaWiki API)
"""
import requests
from typing import List, Optional
from .base_source import BaseSource, SearchResult


class WikimediaCommonsSource(BaseSource):
    """Search Wikimedia Commons for free educational media"""
    
    def __init__(self):
        self.api_url = "https://commons.wikimedia.org/w/api.php"
        self.base_url = "https://commons.wikimedia.org"
        self.headers = {
            'User-Agent': 'Scoolish-AI-Platform/1.0 (Educational; https://scoolish.com)'
        }
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        Search Wikimedia Commons for media files
        
        Args:
            query: Search query
            limit: Maximum number of results (default 10)
        
        Returns:
            List of SearchResult objects
        """
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': query,
                'srnamespace': '6',  # File namespace
                'srlimit': min(limit, 50),
                'srprop': 'snippet|titlesnippet|size',
            }
            
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            if 'query' in data and 'search' in data['query']:
                for item in data['query']['search']:
                    title = item.get('title', '').replace('File:', '')
                    page_id = item.get('pageid', '')
                    snippet = item.get('snippet', '').replace('<span class="searchmatch">', '').replace('</span>', '')
                    size = item.get('size', 0)
                    
                    # Construct file page URL
                    file_url = f"{self.base_url}/wiki/File:{title.replace(' ', '_')}"
                    
                    # Determine media type from extension
                    extension = title.split('.')[-1].lower() if '.' in title else ''
                    media_type = 'unknown'
                    if extension in ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp']:
                        media_type = 'image'
                    elif extension in ['mp4', 'webm', 'ogv']:
                        media_type = 'video'
                    elif extension in ['mp3', 'ogg', 'wav', 'flac']:
                        media_type = 'audio'
                    elif extension in ['pdf']:
                        media_type = 'document'
                    
                    # Icon based on media type
                    icon = {
                        'image': '🖼️',
                        'video': '🎥',
                        'audio': '🔊',
                        'document': '📄',
                        'unknown': '📎'
                    }.get(media_type, '📎')
                    
                    confidence = 0.7 if size > 1000 else 0.5
                    
                    results.append(SearchResult(
                        title=f"{icon} {title}",
                        url=file_url,
                        snippet=snippet or f"Free {media_type} file from Wikimedia Commons",
                        domain='commons.wikimedia.org',
                        source='Wikimedia Commons',
                        source_icon='🖼️',
                        confidence=confidence,
                        metadata={
                            'page_id': page_id,
                            'media_type': media_type,
                            'extension': extension,
                            'size': size,
                            'license': 'Free license (Creative Commons or Public Domain)'
                        }
                    ))
            
            return results[:limit]
            
        except requests.RequestException as e:
            print(f"[WikimediaCommonsSource] Search error: {str(e)}")
            return []
        except Exception as e:
            print(f"[WikimediaCommonsSource] Unexpected error: {str(e)}")
            return []
    
    def is_available(self) -> bool:
        """Check if Wikimedia Commons API is accessible"""
        try:
            response = requests.get(
                self.api_url,
                params={'action': 'query', 'format': 'json', 'meta': 'siteinfo'},
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        except:
            return True
    
    def get_metadata(self) -> dict:
        """Return source metadata"""
        return {
            'name': 'wikimedia_commons',
            'display_name': 'Wikimedia Commons',
            'description': 'Free educational images, videos, and audio',
            'icon': '🖼️',
            'is_free': True,
            'requires_key': False,
            'enabled': True,
            'rate_limit': 'Very generous (same as Wikipedia)',
            'best_for': ['images', 'videos', 'audio', 'educational media', 'illustrations']
        }
