# app/services/stages/organize/collections_service.py
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.ai_service_base import AIServiceBase

log = logging.getLogger(__name__)

class CollectionsService(AIServiceBase):
    """
    Service for organizing documents into collections/boards with smart categorization.
    Creates thematic collections based on content analysis and user preferences.
    """
    
    def __init__(self):
        super().__init__()
        self.service_name = "collections_boards"
        
    def get_service_info(self) -> Dict[str, Any]:
        """
        Return information about the collections service.
        
        Returns:
            Dictionary with service information
        """
        return {
            "service_name": self.service_name,
            "description": "Service for organizing documents into collections/boards with smart categorization",
            "capabilities": [
                "automatic_collections",
                "thematic_grouping",
                "content_categorization",
                "smart_boards_creation"
            ],
            "supported_types": ["topic_based", "content_type", "date_based", "hybrid"],
            "version": "1.0.0"
        }
        
    def create_collections_for_files(self, file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create intelligent collections/boards for organizing multiple files.
        
        Args:
            file_data: List of file analysis data with summaries, topics, etc.
            
        Returns:
            Dict containing collections structure and metadata
        """
        try:
            log.info(f"[Collections] Creating collections for {len(file_data)} files")
            
            # 1. Analyze content themes and topics
            themes = self._extract_common_themes(file_data)
            
            # 2. Create collections based on themes
            collections = self._create_thematic_collections(file_data, themes)
            
            # 3. Add smart organization features
            collections_enhanced = self._enhance_collections(collections, file_data)
            
            # 4. Generate collection metadata
            metadata = self._generate_collection_metadata(collections_enhanced, file_data)
            
            result = {
                "collections": collections_enhanced,
                "themes": themes,
                "metadata": metadata,
                "organization_strategy": "thematic_clustering",
                "created_at": datetime.utcnow().isoformat()
            }
            
            log.info(f"[Collections] Created {len(collections_enhanced)} collections")
            return result
            
        except Exception as e:
            log.error(f"[Collections] Error creating collections: {e}")
            raise
    
    def _extract_common_themes(self, file_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract common themes across all documents."""
        try:
            # Prepare content for analysis
            all_summaries = []
            all_topics = []
            
            for file_info in file_data:
                if file_info.get("summary"):
                    all_summaries.append(file_info["summary"])
                if file_info.get("topics"):
                    all_topics.extend(file_info["topics"])
            
            # Use AI to identify themes
            themes_prompt = f"""
            Analyze the following document summaries and topics to identify 3-7 main themes for organizing these documents into collections.
            
            Document Summaries:
            {chr(10).join([f"- {summary}" for summary in all_summaries[:10]])}
            
            Common Topics:
            {', '.join(set(all_topics[:20]))}
            
            Create themes that are:
            1. Distinct and non-overlapping
            2. Broad enough to contain multiple documents
            3. Specific enough to be meaningful
            
            Return themes as JSON with this structure:
            {{
                "themes": [
                    {{
                        "name": "Theme Name",
                        "description": "Brief description",
                        "keywords": ["keyword1", "keyword2", "keyword3"],
                        "scope": "broad|medium|specific"
                    }}
                ]
            }}
            """
            
            response = self._call_openai_api(themes_prompt, max_tokens=800)
            themes_data = self._parse_json_response(response)
            
            return themes_data.get("themes", [])
            
        except Exception as e:
            log.error(f"[Collections] Error extracting themes: {e}")
            # Fallback to simple categorization
            return [
                {"name": "Primary Documents", "description": "Main content documents", "keywords": ["main", "primary"], "scope": "broad"},
                {"name": "Supporting Materials", "description": "Supporting and reference materials", "keywords": ["support", "reference"], "scope": "medium"},
                {"name": "Miscellaneous", "description": "Other documents", "keywords": ["other", "misc"], "scope": "broad"}
            ]
    
    def _create_thematic_collections(self, file_data: List[Dict[str, Any]], themes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Organize files into thematic collections."""
        collections = []
        
        for theme in themes:
            collection = {
                "id": f"collection_{theme['name'].lower().replace(' ', '_')}",
                "name": theme["name"],
                "description": theme["description"],
                "theme_keywords": theme["keywords"],
                "files": [],
                "total_files": 0,
                "collection_type": "thematic",
                "priority": self._calculate_theme_priority(theme)
            }
            
            # Assign files to this collection based on content matching
            for file_info in file_data:
                if self._file_matches_theme(file_info, theme):
                    collection["files"].append({
                        "file_id": file_info["file_id"],
                        "file_name": file_info.get("file_name", "Unknown"),
                        "relevance_score": self._calculate_relevance_score(file_info, theme),
                        "summary": file_info.get("summary", "")[:200] + "..." if file_info.get("summary", "") else "",
                        "added_to_collection_at": datetime.utcnow().isoformat()
                    })
            
            collection["total_files"] = len(collection["files"])
            
            # Only include collections with files
            if collection["total_files"] > 0:
                collections.append(collection)
        
        return collections
    
    def _enhance_collections(self, collections: List[Dict[str, Any]], file_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add enhanced organization features to collections."""
        enhanced_collections = []
        
        for collection in collections:
            enhanced = collection.copy()
            
            # Add smart features
            enhanced["features"] = {
                "smart_sorting": self._generate_smart_sorting(collection["files"]),
                "suggested_tags": self._generate_collection_tags(collection),
                "related_collections": self._find_related_collections(collection, collections),
                "quick_actions": self._generate_quick_actions(collection)
            }
            
            # Add collection statistics
            enhanced["statistics"] = {
                "total_files": enhanced["total_files"],
                "avg_relevance_score": self._calculate_avg_relevance(collection["files"]),
                "content_diversity": self._calculate_content_diversity(collection["files"]),
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Add visualization data
            enhanced["visualization"] = {
                "board_layout": "grid",
                "color_scheme": self._assign_color_scheme(collection),
                "icon": self._suggest_collection_icon(collection),
                "sort_options": ["relevance", "date_added", "alphabetical", "file_size"]
            }
            
            enhanced_collections.append(enhanced)
        
        return enhanced_collections
    
    def _generate_collection_metadata(self, collections: List[Dict[str, Any]], file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate overall metadata for the collections system."""
        return {
            "total_collections": len(collections),
            "total_files_organized": len(file_data),
            "organization_efficiency": len([f for c in collections for f in c["files"]]) / len(file_data) if file_data else 0,
            "most_populated_collection": max(collections, key=lambda x: x["total_files"])["name"] if collections else None,
            "collection_distribution": {c["name"]: c["total_files"] for c in collections},
            "suggested_improvements": self._suggest_organization_improvements(collections),
            "created_at": datetime.utcnow().isoformat()
        }
    
    def _file_matches_theme(self, file_info: Dict[str, Any], theme: Dict[str, Any]) -> bool:
        """Check if a file matches a given theme."""
        file_content = f"{file_info.get('summary', '')} {' '.join(file_info.get('topics', []))}"
        theme_keywords = theme.get("keywords", [])
        
        # Simple keyword matching (can be enhanced with semantic similarity)
        matches = sum(1 for keyword in theme_keywords if keyword.lower() in file_content.lower())
        return matches >= 1  # At least one keyword match
    
    def _calculate_relevance_score(self, file_info: Dict[str, Any], theme: Dict[str, Any]) -> float:
        """Calculate how relevant a file is to a theme (0.0 to 1.0)."""
        file_content = f"{file_info.get('summary', '')} {' '.join(file_info.get('topics', []))}"
        theme_keywords = theme.get("keywords", [])
        
        if not theme_keywords:
            return 0.5
            
        matches = sum(1 for keyword in theme_keywords if keyword.lower() in file_content.lower())
        return min(matches / len(theme_keywords), 1.0)
    
    def _calculate_theme_priority(self, theme: Dict[str, Any]) -> int:
        """Calculate priority order for themes (1 = highest)."""
        scope_priorities = {"specific": 1, "medium": 2, "broad": 3}
        return scope_priorities.get(theme.get("scope", "broad"), 3)
    
    def _generate_smart_sorting(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate smart sorting options for collection files."""
        return {
            "by_relevance": sorted(files, key=lambda x: x.get("relevance_score", 0), reverse=True),
            "by_date_added": sorted(files, key=lambda x: x.get("added_to_collection_at", ""), reverse=True),
            "recommended_order": "by_relevance"  # Default recommendation
        }
    
    def _generate_collection_tags(self, collection: Dict[str, Any]) -> List[str]:
        """Generate suggested tags for a collection."""
        base_tags = collection.get("theme_keywords", [])
        additional_tags = [collection["name"].lower(), collection["collection_type"]]
        return list(set(base_tags + additional_tags))
    
    def _find_related_collections(self, collection: Dict[str, Any], all_collections: List[Dict[str, Any]]) -> List[str]:
        """Find collections related to the current one."""
        related = []
        current_keywords = set(collection.get("theme_keywords", []))
        
        for other_collection in all_collections:
            if other_collection["id"] != collection["id"]:
                other_keywords = set(other_collection.get("theme_keywords", []))
                overlap = len(current_keywords.intersection(other_keywords))
                if overlap > 0:
                    related.append(other_collection["name"])
        
        return related[:3]  # Limit to 3 related collections
    
    def _generate_quick_actions(self, collection: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate quick action buttons for collections."""
        return [
            {"action": "add_files", "label": "Add Files", "icon": "plus"},
            {"action": "export_collection", "label": "Export", "icon": "download"},
            {"action": "share_collection", "label": "Share", "icon": "share"},
            {"action": "merge_collection", "label": "Merge", "icon": "merge"},
            {"action": "duplicate_collection", "label": "Duplicate", "icon": "copy"}
        ]
    
    def _calculate_avg_relevance(self, files: List[Dict[str, Any]]) -> float:
        """Calculate average relevance score for files in collection."""
        if not files:
            return 0.0
        scores = [f.get("relevance_score", 0) for f in files]
        return sum(scores) / len(scores)
    
    def _calculate_content_diversity(self, files: List[Dict[str, Any]]) -> float:
        """Calculate content diversity within collection (0.0 to 1.0)."""
        if len(files) <= 1:
            return 0.0
        
        # Simple diversity based on summary uniqueness
        summaries = [f.get("summary", "") for f in files]
        unique_words = set()
        total_words = 0
        
        for summary in summaries:
            words = summary.lower().split()
            unique_words.update(words)
            total_words += len(words)
        
        return len(unique_words) / max(total_words, 1) if total_words > 0 else 0.0
    
    def _assign_color_scheme(self, collection: Dict[str, Any]) -> str:
        """Assign a color scheme based on collection theme."""
        theme_colors = {
            "technical": "blue",
            "business": "green", 
            "creative": "purple",
            "research": "orange",
            "education": "teal"
        }
        
        collection_name = collection["name"].lower()
        for theme, color in theme_colors.items():
            if theme in collection_name:
                return color
        
        return "gray"  # Default color
    
    def _suggest_collection_icon(self, collection: Dict[str, Any]) -> str:
        """Suggest an appropriate icon for the collection."""
        name_lower = collection["name"].lower()
        
        icon_mapping = {
            "research": "microscope",
            "analysis": "chart-bar",
            "report": "file-text",
            "data": "database",
            "presentation": "presentation",
            "meeting": "users",
            "project": "folder",
            "reference": "bookmark"
        }
        
        for keyword, icon in icon_mapping.items():
            if keyword in name_lower:
                return icon
        
        return "folder"  # Default icon
    
    def _suggest_organization_improvements(self, collections: List[Dict[str, Any]]) -> List[str]:
        """Suggest improvements to the organization structure."""
        suggestions = []
        
        # Check for empty collections
        empty_collections = [c for c in collections if c["total_files"] == 0]
        if empty_collections:
            suggestions.append(f"Consider removing {len(empty_collections)} empty collections")
        
        # Check for overpopulated collections
        large_collections = [c for c in collections if c["total_files"] > 10]
        if large_collections:
            suggestions.append(f"Consider splitting {len(large_collections)} large collections")
        
        # Check for similar collections
        if len(collections) > 5:
            suggestions.append("Consider merging similar collections to reduce complexity")
        
        return suggestions
