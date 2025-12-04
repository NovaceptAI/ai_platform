"""
Open Library Search Source - Books and authors
Free, no API key required
"""
import requests
from typing import List
from app.services.sources.base_source import BaseSource, SearchResult


class OpenLibrarySource(BaseSource):
    """Open Library book and author search"""
    
    def __init__(self):
        super().__init__()
        self.name = 'openlibrary'
        self.icon = '📖'
        self.description = 'Open Library - Books and authors'
        self.is_free = True
        self.requires_key = False
        self.base_url = 'https://openlibrary.org'
        self.rate_limit = 'Reasonable use'
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search Open Library"""
        results = []
        
        # Skip very short queries (OpenLibrary doesn't handle them well)
        if len(query.strip()) < 3:
            return results
        
        try:
            search_url = f'{self.base_url}/search.json'
            params = {
                'q': query,
                'limit': limit,
                'fields': 'key,title,author_name,first_publish_year,isbn,subject,cover_i'
            }
            
            headers = {
                'User-Agent': 'Scoolish-AI-Platform/1.0 (Educational; https://scoolish.com)'
            }
            
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            # OpenLibrary returns 422 for queries that are too ambiguous - just return empty
            if response.status_code == 422:
                return results
                
            response.raise_for_status()
            data = response.json()
            
            docs = data.get('docs', [])
            
            for i, doc in enumerate(docs[:limit]):
                title = doc.get('title', 'Untitled')
                authors = doc.get('author_name', [])
                year = doc.get('first_publish_year', '')
                key = doc.get('key', '')
                cover_id = doc.get('cover_i', '')
                subjects = doc.get('subject', [])
                
                # Build snippet
                snippet_parts = []
                if authors:
                    snippet_parts.append(f"by {', '.join(authors[:3])}")
                if year:
                    snippet_parts.append(f"({year})")
                if subjects:
                    snippet_parts.append(f"Subjects: {', '.join(subjects[:3])}")
                
                snippet = ' • '.join(snippet_parts)
                
                # Build URL
                url = f'{self.base_url}{key}' if key else f'{self.base_url}/search?q={query}'
                
                results.append(SearchResult(
                    title=title,
                    snippet=snippet,
                    url=url,
                    domain='openlibrary.org',
                    source='openlibrary',
                    source_icon=self.icon,
                    confidence=1.0 - (i * 0.05),
                    metadata={
                        'type': 'book',
                        'authors': authors,
                        'year': year,
                        'subjects': subjects[:5],
                        'cover_url': f'https://covers.openlibrary.org/b/id/{cover_id}-M.jpg' if cover_id else None,
                        'isbn': doc.get('isbn', [])[:3]
                    }
                ))
            
        except Exception as e:
            raise Exception(f'Open Library search failed: {str(e)}')
        
        return results
    
    def is_available(self) -> bool:
        """Check if Open Library API is accessible"""
        # Open Library is always available, check at search time
        return True
