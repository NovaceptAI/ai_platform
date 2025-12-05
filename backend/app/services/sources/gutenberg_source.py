"""
Project Gutenberg Search Source - Free classic literature and books
Uses Project Gutenberg's catalog API and web scraping
"""
import requests
from typing import List, Optional
from .base_source import BaseSource, SearchResult


class ProjectGutenbergSource(BaseSource):
    """Search Project Gutenberg for free classic books (70,000+ titles)"""
    
    def __init__(self):
        self.search_url = "https://www.gutenberg.org/ebooks/search/"
        self.base_url = "https://www.gutenberg.org"
        self.headers = {
            'User-Agent': 'Scoolish-AI-Platform/1.0 (Educational; https://scoolish.com)'
        }
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        Search Project Gutenberg catalog
        
        Args:
            query: Search query
            limit: Maximum number of results (default 10)
        
        Returns:
            List of SearchResult objects
        """
        try:
            params = {
                'query': query,
                'submit_search': 'Go!'
            }
            
            response = requests.get(self.search_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML to extract book information
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            book_items = soup.find_all('li', class_='booklink')[:limit]
            
            for item in book_items:
                try:
                    # Extract book information
                    title_elem = item.find('span', class_='title')
                    author_elem = item.find('span', class_='subtitle')
                    
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    author = author_elem.get_text(strip=True) if author_elem else 'Unknown Author'
                    
                    # Get book link
                    link_elem = item.find('a', class_='link')
                    if link_elem and link_elem.get('href'):
                        book_url = f"{self.base_url}{link_elem['href']}"
                    else:
                        continue
                    
                    # Extract book ID from URL
                    book_id = ''
                    if '/ebooks/' in book_url:
                        book_id = book_url.split('/ebooks/')[-1]
                    
                    # Create snippet
                    snippet = f"Classic book by {author}. Available in multiple formats (HTML, EPUB, Kindle, Plain Text)."
                    
                    results.append(SearchResult(
                        title=f"📖 {title}",
                        url=book_url,
                        snippet=snippet,
                        domain='gutenberg.org',
                        source='Project Gutenberg',
                        source_icon='📖',
                        confidence=0.8,
                        metadata={
                            'author': author,
                            'book_id': book_id,
                            'formats': ['HTML', 'EPUB', 'Kindle', 'Plain Text'],
                            'license': 'Public Domain',
                            'download_available': True
                        }
                    ))
                    
                except Exception as e:
                    print(f"[ProjectGutenbergSource] Error parsing item: {str(e)}")
                    continue
            
            return results[:limit]
            
        except requests.RequestException as e:
            print(f"[ProjectGutenbergSource] Search error: {str(e)}")
            return []
        except Exception as e:
            print(f"[ProjectGutenbergSource] Unexpected error: {str(e)}")
            return []
    
    def is_available(self) -> bool:
        """Check if Project Gutenberg is accessible"""
        try:
            response = requests.get(
                self.base_url,
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        except:
            return True
    
    def get_metadata(self) -> dict:
        """Return source metadata"""
        return {
            'name': 'gutenberg',
            'display_name': 'Project Gutenberg',
            'description': 'Free classic literature and public domain books',
            'icon': '📖',
            'is_free': True,
            'requires_key': False,
            'enabled': True,
            'rate_limit': 'Be respectful, no strict limit',
            'best_for': ['classic literature', 'historical texts', 'public domain books', 'educational reading']
        }
