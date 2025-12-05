"""
Google Books Search Source - Book search and preview
Uses Google Books API v1 (completely free, no API key required for basic searches)
"""
import requests
from typing import List, Optional
from .base_source import BaseSource, SearchResult


class GoogleBooksSource(BaseSource):
    """Search Google Books for books, textbooks, and educational content"""
    
    def __init__(self):
        self.base_url = "https://www.googleapis.com/books/v1/volumes"
        self.headers = {
            'User-Agent': 'Scoolish-AI-Platform/1.0 (Educational; https://scoolish.com)'
        }
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        Search Google Books
        
        Args:
            query: Search query
            limit: Maximum number of results (default 10)
        
        Returns:
            List of SearchResult objects
        """
        try:
            params = {
                'q': query,
                'maxResults': min(limit, 40),  # Google Books max is 40
                'printType': 'all',
                'orderBy': 'relevance'
            }
            
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            if 'items' in data:
                for item in data['items']:
                    volume_info = item.get('volumeInfo', {})
                    
                    title = volume_info.get('title', 'Untitled')
                    authors = volume_info.get('authors', [])
                    description = volume_info.get('description', '')
                    publisher = volume_info.get('publisher', '')
                    published_date = volume_info.get('publishedDate', '')
                    page_count = volume_info.get('pageCount', 0)
                    categories = volume_info.get('categories', [])
                    preview_link = volume_info.get('previewLink', '')
                    info_link = volume_info.get('infoLink', '')
                    
                    # Create snippet
                    snippet = description[:250] if description else f"Book by {', '.join(authors[:2])}" if authors else "Book"
                    
                    # Confidence based on data completeness
                    confidence = 0.7
                    if description:
                        confidence += 0.15
                    if page_count > 50:
                        confidence += 0.1
                    if preview_link:
                        confidence += 0.05
                    
                    results.append(SearchResult(
                        title=f"{title} - {', '.join(authors[:2])}" if authors else title,
                        url=preview_link or info_link,
                        snippet=snippet,
                        domain='books.google.com',
                        source='Google Books',
                        source_icon='📚',
                        confidence=min(confidence, 1.0),
                        metadata={
                            'authors': authors,
                            'publisher': publisher,
                            'published_date': published_date,
                            'page_count': page_count,
                            'categories': categories,
                            'preview_available': bool(preview_link)
                        }
                    ))
            
            return results[:limit]
            
        except requests.RequestException as e:
            print(f"[GoogleBooksSource] Search error: {str(e)}")
            return []
        except Exception as e:
            print(f"[GoogleBooksSource] Unexpected error: {str(e)}")
            return []
    
    def is_available(self) -> bool:
        """Check if Google Books API is accessible"""
        try:
            response = requests.get(
                f"{self.base_url}?q=test&maxResults=1",
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        except:
            return True  # Assume available
    
    def get_metadata(self) -> dict:
        """Return source metadata"""
        return {
            'name': 'google_books',
            'display_name': 'Google Books',
            'description': 'Search millions of books and get previews',
            'icon': '📚',
            'is_free': True,
            'requires_key': False,
            'enabled': True,
            'rate_limit': 'Generous (1000+ requests/day)',
            'best_for': ['books', 'textbooks', 'academic content', 'research materials']
        }
