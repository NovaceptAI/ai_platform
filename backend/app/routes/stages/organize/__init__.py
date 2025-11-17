# app/routes/stages/organize/__init__.py
"""
Organize stage route modules.

This package contains individual route files for each organize stage tool:
- collections_routes.py: Document collections management
- tags_routes.py: Tag taxonomy generation  
- clusters_routes.py: Document clustering
- concept_graph_routes.py: Concept graph generation
- saved_views_routes.py: Saved views creation

Each module provides /start, /progress, and /results endpoints for their respective tools.
"""

from .collections_routes import collections_bp
from .tags_routes import tags_bp
from .clusters_routes import clusters_bp
from .concept_graph_routes import concept_graph_bp
from .saved_views_routes import saved_views_bp

__all__ = [
    'collections_bp',
    'tags_bp', 
    'clusters_bp',
    'concept_graph_bp',
    'saved_views_bp'
]
