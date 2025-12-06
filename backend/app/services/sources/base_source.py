"""
Base class for all search sources with unified interface
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse


@dataclass
class SearchResult:
    """Unified result format across all sources"""
    title: str
    snippet: str
    url: str
    domain: str
    source: str  # 'wikipedia', 'duckduckgo', etc.
    source_icon: str  # emoji or icon identifier
    metadata: Dict[str, Any] = None
    confidence: float = 0.0  # relevance score (0-1)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        # Auto-extract domain if not provided
        if not self.domain and self.url:
            try:
                self.domain = urlparse(self.url).netloc
            except Exception:
                self.domain = ''

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class BaseSource(ABC):
    """Abstract base class for search sources"""
    
    def __init__(self):
        self.name = self.__class__.__name__.replace('Source', '').lower()
        self.is_free = True
        self.requires_key = False
        self.rate_limit = None
        self.icon = "🔍"  # default icon
        self.description = "Search source"
        self.enabled = True
    
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        Execute search and return normalized results
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of SearchResult objects
        """
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return source metadata"""
        return {
            'name': self.name,
            'display_name': self.name.title(),
            'icon': self.icon,
            'description': self.description,
            'is_free': self.is_free,
            'requires_key': self.requires_key,
            'rate_limit': self.rate_limit,
            'enabled': self.enabled and self.is_available(),
        }
    
    def is_available(self) -> bool:
        """Check if source is configured and working"""
        # Override in subclasses to check API keys, connectivity, etc.
        return True
    
    def test_connection(self) -> Dict[str, Any]:
        """Test source connectivity and return status"""
        try:
            results = self.search("test", limit=1)
            return {
                'status': 'ok',
                'available': True,
                'message': f'{self.name} is working',
                'test_results': len(results)
            }
        except Exception as e:
            return {
                'status': 'error',
                'available': False,
                'message': str(e),
                'error_type': type(e).__name__
            }
