"""
ArXiv Search Source - Academic papers
Free, no API key required
"""
import requests
import xml.etree.ElementTree as ET
from typing import List
from app.services.sources.base_source import BaseSource, SearchResult


class ArxivSource(BaseSource):
    """ArXiv academic paper search"""
    
    def __init__(self):
        super().__init__()
        self.name = 'arxiv'
        self.icon = '📄'
        self.description = 'ArXiv - Academic papers and preprints'
        self.is_free = True
        self.requires_key = False
        self.base_url = 'http://export.arxiv.org/api/query'
        self.rate_limit = '1 req per 3s (recommended)'
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search ArXiv papers"""
        results = []
        
        try:
            params = {
                'search_query': f'all:{query}',
                'start': 0,
                'max_results': limit,
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            headers = {
                'User-Agent': 'Scoolish-AI-Platform/1.0 (Educational; https://scoolish.com)'
            }
            
            response = requests.get(self.base_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            
            # XML namespaces
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            entries = root.findall('atom:entry', ns)
            
            for i, entry in enumerate(entries):
                title_elem = entry.find('atom:title', ns)
                summary_elem = entry.find('atom:summary', ns)
                link_elem = entry.find('atom:id', ns)
                published_elem = entry.find('atom:published', ns)
                
                # Get authors
                authors = []
                for author in entry.findall('atom:author', ns):
                    name_elem = author.find('atom:name', ns)
                    if name_elem is not None:
                        authors.append(name_elem.text)
                
                # Get categories
                categories = []
                for category in entry.findall('atom:category', ns):
                    term = category.get('term')
                    if term:
                        categories.append(term)
                
                title = title_elem.text.strip() if title_elem is not None else ''
                summary = summary_elem.text.strip() if summary_elem is not None else ''
                url = link_elem.text if link_elem is not None else ''
                published = published_elem.text if published_elem is not None else ''
                
                results.append(SearchResult(
                    title=title,
                    snippet=summary[:300] + '...' if len(summary) > 300 else summary,
                    url=url,
                    domain='arxiv.org',
                    source='arxiv',
                    source_icon=self.icon,
                    confidence=1.0 - (i * 0.05),
                    metadata={
                        'type': 'academic_paper',
                        'authors': authors,
                        'categories': categories,
                        'published': published,
                        'pdf_url': url.replace('/abs/', '/pdf/') + '.pdf' if '/abs/' in url else ''
                    }
                ))
            
        except Exception as e:
            raise Exception(f'ArXiv search failed: {str(e)}')
        
        return results
    
    def is_available(self) -> bool:
        """Check if ArXiv API is accessible"""
        # ArXiv is always available, check at search time
        return True
