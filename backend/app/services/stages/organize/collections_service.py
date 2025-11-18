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
            
            messages = [
                {"role": "system", "content": "You are an expert at analyzing documents and identifying themes."},
                {"role": "user", "content": themes_prompt}
            ]
            response = self._make_openai_call(messages, max_tokens=800)
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
        """Organize files and sections into thematic collections."""
        collections = []
        assigned_files = set()  # Track which files have been assigned
        assigned_sections = set()  # Track which sections have been assigned

        for theme in themes:
            collection = {
                "id": f"collection_{theme['name'].lower().replace(' ', '_')}",
                "name": theme["name"],
                "description": theme["description"],
                "theme_keywords": theme["keywords"],
                "files": [],
                "sections": [],  # NEW: Section-level mapping
                "total_files": 0,
                "total_sections": 0,
                "collection_type": "thematic",
                "priority": self._calculate_theme_priority(theme)
            }

            # Assign files to this collection based on content matching
            for file_info in file_data:
                file_matched = False

                # Check if file has sections - if so, match at section level
                if file_info.get("sections"):
                    for section in file_info["sections"]:
                        if self._section_matches_theme(section, theme):
                            section_key = f"{file_info['file_id']}_{section.get('section_id', '')}"
                            collection["sections"].append({
                                "file_id": file_info["file_id"],
                                "file_name": file_info.get("file_name", "Unknown"),
                                "section_id": section.get("section_id", ""),
                                "section_title": section.get("title", "Untitled Section"),
                                "section_summary": section.get("summary", "")[:200] + "..." if section.get("summary", "") else "",
                                "page_range": f"{section.get('page_start', 0)}-{section.get('page_end', 0)}",
                                "page_start": section.get("page_start", 0),
                                "page_end": section.get("page_end", 0),
                                "relevance_score": self._calculate_section_relevance(section, theme),
                                "tags": section.get("tags", []),
                                "added_to_collection_at": datetime.utcnow().isoformat()
                            })
                            assigned_sections.add(section_key)
                            file_matched = True

                # Also match at file level (for files without sections or overall match)
                if self._file_matches_theme(file_info, theme):
                    collection["files"].append({
                        "file_id": file_info["file_id"],
                        "file_name": file_info.get("file_name", "Unknown"),
                        "relevance_score": self._calculate_relevance_score(file_info, theme),
                        "summary": file_info.get("summary", "")[:200] + "..." if file_info.get("summary", "") else "",
                        "has_sections": len(file_info.get("sections", [])) > 0,
                        "section_count": len(file_info.get("sections", [])),
                        "added_to_collection_at": datetime.utcnow().isoformat()
                    })
                    assigned_files.add(file_info["file_id"])
                    file_matched = True

            collection["total_files"] = len(collection["files"])
            collection["total_sections"] = len(collection["sections"])

            # Only include collections with files or sections
            if collection["total_files"] > 0 or collection["total_sections"] > 0:
                collections.append(collection)

        # If no files were assigned to any collection, create a default "All Documents" collection
        if not assigned_files and not assigned_sections and file_data:
            log.warning("[Collections] No files matched any themes, creating default collection")
            default_collection = {
                "id": "collection_all_documents",
                "name": "All Documents",
                "description": "All uploaded documents",
                "theme_keywords": ["document", "file"],
                "files": [],
                "sections": [],
                "total_files": len(file_data),
                "total_sections": 0,
                "collection_type": "default",
                "priority": 99
            }

            for file_info in file_data:
                default_collection["files"].append({
                    "file_id": file_info["file_id"],
                    "file_name": file_info.get("file_name", "Unknown"),
                    "relevance_score": 1.0,
                    "summary": file_info.get("summary", "")[:200] + "..." if file_info.get("summary", "") else "",
                    "has_sections": len(file_info.get("sections", [])) > 0,
                    "section_count": len(file_info.get("sections", [])),
                    "added_to_collection_at": datetime.utcnow().isoformat()
                })

                # Also add all sections to default collection
                for section in file_info.get("sections", []):
                    default_collection["sections"].append({
                        "file_id": file_info["file_id"],
                        "file_name": file_info.get("file_name", "Unknown"),
                        "section_id": section.get("section_id", ""),
                        "section_title": section.get("title", "Untitled Section"),
                        "section_summary": section.get("summary", "")[:200] + "..." if section.get("summary", "") else "",
                        "page_range": f"{section.get('page_start', 0)}-{section.get('page_end', 0)}",
                        "page_start": section.get("page_start", 0),
                        "page_end": section.get("page_end", 0),
                        "relevance_score": 1.0,
                        "tags": section.get("tags", []),
                        "added_to_collection_at": datetime.utcnow().isoformat()
                    })
                    default_collection["total_sections"] += 1

            collections.append(default_collection)

        return collections

    def _section_matches_theme(self, section: Dict[str, Any], theme: Dict[str, Any]) -> bool:
        """Check if a section matches a given theme."""
        # Gather section content for matching
        section_content_parts = []

        # Add section title
        if section.get("title"):
            section_content_parts.append(str(section.get("title", "")))

        # Add section summary
        if section.get("summary"):
            section_content_parts.append(str(section.get("summary", "")))

        # Add section tags
        if section.get("tags"):
            for tag in section.get("tags", []):
                if isinstance(tag, str):
                    section_content_parts.append(tag)

        # Add section entities
        if section.get("entities"):
            for entity in section.get("entities", []):
                if isinstance(entity, str):
                    section_content_parts.append(entity)

        # Filter out empty strings and join
        section_content_parts = [part for part in section_content_parts if part.strip()]
        section_content = ' '.join(section_content_parts).lower()

        # If section has no content, don't match
        if not section_content.strip():
            return False

        theme_keywords = theme.get("keywords", [])

        # Keyword matching
        matches = sum(1 for keyword in theme_keywords if keyword.lower() in section_content)
        return matches >= 1  # At least one keyword match

    def _calculate_section_relevance(self, section: Dict[str, Any], theme: Dict[str, Any]) -> float:
        """Calculate how relevant a section is to a theme (0.0 to 1.0)."""
        # Gather section content
        section_content_parts = []

        if section.get("title"):
            section_content_parts.append(str(section.get("title", "")))
        if section.get("summary"):
            section_content_parts.append(str(section.get("summary", "")))
        if section.get("tags"):
            for tag in section.get("tags", []):
                if isinstance(tag, str):
                    section_content_parts.append(tag)
        if section.get("entities"):
            for entity in section.get("entities", []):
                if isinstance(entity, str):
                    section_content_parts.append(entity)

        section_content_parts = [part for part in section_content_parts if part.strip()]
        section_content = ' '.join(section_content_parts).lower()
        theme_keywords = theme.get("keywords", [])

        if not theme_keywords:
            return 0.5

        matches = sum(1 for keyword in theme_keywords if keyword.lower() in section_content)
        return min(matches / len(theme_keywords), 1.0)
    
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

            # Add collection statistics (including section stats)
            sections = collection.get("sections", [])
            enhanced["statistics"] = {
                "total_files": enhanced["total_files"],
                "total_sections": enhanced.get("total_sections", len(sections)),
                "avg_relevance_score": self._calculate_avg_relevance(collection["files"]),
                "avg_section_relevance": self._calculate_avg_relevance(sections) if sections else 0.0,
                "content_diversity": self._calculate_content_diversity(collection["files"]),
                "last_updated": datetime.utcnow().isoformat()
            }

            # Add visualization data
            enhanced["visualization"] = {
                "board_layout": "grid",
                "color_scheme": self._assign_color_scheme(collection),
                "icon": self._suggest_collection_icon(collection),
                "sort_options": ["relevance", "date_added", "alphabetical", "file_size", "page_range"]
            }

            enhanced_collections.append(enhanced)

        return enhanced_collections
    
    def _generate_collection_metadata(self, collections: List[Dict[str, Any]], file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate overall metadata for the collections system."""
        # Calculate organization efficiency: percentage of files that were successfully categorized
        # (excluding the default "All Documents" collection)
        non_default_collections = [c for c in collections if c.get("collection_type") != "default"]

        if file_data and non_default_collections:
            # Count unique files that were assigned to at least one thematic collection
            assigned_file_ids = set()
            for collection in non_default_collections:
                for file_item in collection.get("files", []):
                    assigned_file_ids.add(file_item.get("file_id"))
            organization_efficiency = len(assigned_file_ids) / len(file_data)
        else:
            organization_efficiency = 0.0

        return {
            "total_collections": len(collections),
            "total_files_organized": len(file_data),
            "organization_efficiency": min(organization_efficiency, 1.0),  # Cap at 1.0
            "most_populated_collection": max(collections, key=lambda x: x["total_files"])["name"] if collections else None,
            "collection_distribution": {c["name"]: c["total_files"] for c in collections},
            "suggested_improvements": self._suggest_organization_improvements(collections),
            "created_at": datetime.utcnow().isoformat()
        }
    
    def _file_matches_theme(self, file_info: Dict[str, Any], theme: Dict[str, Any]) -> bool:
        """Check if a file matches a given theme."""
        # Gather all file content for matching
        file_content_parts = []

        # Add summary
        if file_info.get('summary'):
            file_content_parts.append(str(file_info.get('summary', '')))

        # Add topics (ensure they're strings)
        if file_info.get('topics'):
            topics = file_info.get('topics', [])
            for topic in topics:
                if isinstance(topic, str):
                    file_content_parts.append(topic)
                elif isinstance(topic, dict):
                    # Extract string value from dict
                    file_content_parts.append(str(topic.get('label') or topic.get('name') or topic.get('topic', '')))

        # Add keywords if available (ensure they're strings)
        if file_info.get('keywords'):
            keywords = file_info.get('keywords', [])
            for keyword in keywords:
                if isinstance(keyword, str):
                    file_content_parts.append(keyword)
                elif isinstance(keyword, dict):
                    file_content_parts.append(str(keyword.get('text') or keyword.get('value', '')))

        # Add file name (sometimes the name is descriptive)
        if file_info.get('file_name'):
            file_content_parts.append(str(file_info.get('file_name', '')))

        # Filter out empty strings and join
        file_content_parts = [part for part in file_content_parts if part.strip()]
        file_content = ' '.join(file_content_parts).lower()

        # If file has no content, assign to broad/general themes
        if not file_content.strip():
            return theme.get("scope") == "broad"

        theme_keywords = theme.get("keywords", [])

        # Simple keyword matching (can be enhanced with semantic similarity)
        matches = sum(1 for keyword in theme_keywords if keyword.lower() in file_content)
        return matches >= 1  # At least one keyword match
    
    def _calculate_relevance_score(self, file_info: Dict[str, Any], theme: Dict[str, Any]) -> float:
        """Calculate how relevant a file is to a theme (0.0 to 1.0)."""
        # Gather all file content for matching (same as _file_matches_theme)
        file_content_parts = []

        # Add summary
        if file_info.get('summary'):
            file_content_parts.append(str(file_info.get('summary', '')))

        # Add topics (ensure they're strings)
        if file_info.get('topics'):
            topics = file_info.get('topics', [])
            for topic in topics:
                if isinstance(topic, str):
                    file_content_parts.append(topic)
                elif isinstance(topic, dict):
                    file_content_parts.append(str(topic.get('label') or topic.get('name') or topic.get('topic', '')))

        # Add keywords if available (ensure they're strings)
        if file_info.get('keywords'):
            keywords = file_info.get('keywords', [])
            for keyword in keywords:
                if isinstance(keyword, str):
                    file_content_parts.append(keyword)
                elif isinstance(keyword, dict):
                    file_content_parts.append(str(keyword.get('text') or keyword.get('value', '')))

        # Add file name
        if file_info.get('file_name'):
            file_content_parts.append(str(file_info.get('file_name', '')))

        # Filter out empty strings and join
        file_content_parts = [part for part in file_content_parts if part.strip()]
        file_content = ' '.join(file_content_parts).lower()
        theme_keywords = theme.get("keywords", [])

        if not theme_keywords:
            return 0.5

        matches = sum(1 for keyword in theme_keywords if keyword.lower() in file_content)
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
        if len(files) == 0:
            return 0.0

        if len(files) == 1:
            # Single file gets a baseline diversity score
            return 0.5

        # Calculate diversity based on multiple factors
        diversity_scores = []

        # 1. Summary diversity - check how different the summaries are
        summaries = [f.get("summary", "").lower() for f in files if f.get("summary")]
        if len(summaries) >= 2:
            unique_words_per_summary = []
            for summary in summaries:
                words = set(summary.split())
                unique_words_per_summary.append(words)

            # Calculate Jaccard distance between summaries (how different they are)
            differences = []
            for i in range(len(unique_words_per_summary)):
                for j in range(i + 1, len(unique_words_per_summary)):
                    intersection = len(unique_words_per_summary[i] & unique_words_per_summary[j])
                    union = len(unique_words_per_summary[i] | unique_words_per_summary[j])
                    if union > 0:
                        # Jaccard distance = 1 - Jaccard similarity
                        differences.append(1.0 - (intersection / union))

            if differences:
                diversity_scores.append(sum(differences) / len(differences))

        # 2. File name diversity (different file names = more diverse)
        file_names = [f.get("file_name", "").lower() for f in files if f.get("file_name")]
        if len(file_names) >= 2:
            unique_file_names = len(set(file_names))
            file_name_diversity = unique_file_names / len(file_names)
            diversity_scores.append(file_name_diversity)

        # 3. Relevance score variance (more variance = more diverse content quality)
        relevance_scores = [f.get("relevance_score", 0) for f in files]
        if len(relevance_scores) >= 2:
            avg_relevance = sum(relevance_scores) / len(relevance_scores)
            variance = sum((score - avg_relevance) ** 2 for score in relevance_scores) / len(relevance_scores)
            # Normalize variance to 0-1 range (variance of 0.25 = max diversity)
            relevance_diversity = min(variance / 0.25, 1.0)
            diversity_scores.append(relevance_diversity)

        # Return average of all diversity metrics
        if diversity_scores:
            return sum(diversity_scores) / len(diversity_scores)
        else:
            return 0.5  # Default for collections with insufficient data
    
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
