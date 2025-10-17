# app/services/stages/organize/saved_views_service.py
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from app.services.ai_service_base import AIServiceBase

log = logging.getLogger(__name__)

class SavedViewsService(AIServiceBase):
    """
    Service for creating and managing custom document views and filters.
    Enables users to save personalized organization schemes and quick access patterns.
    """
    
    def __init__(self):
        super().__init__()
        self.service_name = "saved_views"
        
    def get_service_info(self) -> Dict[str, Any]:
        """
        Return information about the saved views service.
        
        Returns:
            Dictionary with service information
        """
        return {
            "service_name": self.service_name,
            "description": "Service for creating and managing custom document views and filters",
            "capabilities": [
                "custom_views_creation",
                "personalized_organization",
                "filter_management",
                "quick_access_patterns"
            ],
            "supported_views": ["topic_based", "date_based", "type_based", "custom_filters"],
            "version": "1.0.0"
        }
        
    def create_saved_views(self, file_data: List[Dict[str, Any]], organization_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create intelligent saved views based on document analysis and organization patterns.
        
        Args:
            file_data: List of file analysis data
            organization_data: Data from other organization tools (collections, clusters, etc.)
            
        Returns:
            Dict containing saved views and management features
        """
        try:
            log.info(f"[SavedViews] Creating views for {len(file_data)} files")
            
            # Log file data structure for debugging
            if file_data:
                sample_file = file_data[0]
                log.info(f"[SavedViews] Sample file data keys: {list(sample_file.keys())}")
                log.info(f"[SavedViews] File has topics: {len(sample_file.get('topics', []))}")
                log.info(f"[SavedViews] File has entities: {len(sample_file.get('entities', {}))}")
                log.info(f"[SavedViews] File has collections: {len(sample_file.get('collections', []))}")
            
            # 1. Generate smart default views
            default_views = self._generate_default_views(file_data, organization_data)
            log.info(f"[SavedViews] Generated {len(default_views)} default views")
            
            # 2. Create contextual views based on content patterns
            contextual_views = self._create_contextual_views(file_data, organization_data)
            log.info(f"[SavedViews] Generated {len(contextual_views)} contextual views")
            
            # 3. Build filter combinations
            filter_combinations = self._build_filter_combinations(file_data)
            
            # 4. Generate view templates for common use cases
            view_templates = self._create_view_templates()
            
            # 5. Create view management features
            management_features = self._create_management_features(default_views + contextual_views)
            
            # 6. Generate usage analytics framework
            analytics_framework = self._create_analytics_framework()
            
            result = {
                "default_views": default_views,
                "contextual_views": contextual_views,
                "filter_combinations": filter_combinations,
                "view_templates": view_templates,
                "management_features": management_features,
                "analytics_framework": analytics_framework,
                "total_views": len(default_views) + len(contextual_views),
                "created_at": datetime.utcnow().isoformat()
            }
            
            log.info(f"[SavedViews] Created {result['total_views']} saved views")
            return result
            
        except Exception as e:
            log.error(f"[SavedViews] Error creating saved views: {e}")
            raise
    
    def _generate_default_views(self, file_data: List[Dict[str, Any]], organization_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate smart default views based on common patterns."""
        
        default_views = []
        
        # 0. All Files View (always created)
        default_views.append({
            "view_id": "all_files",
            "name": "All Files",
            "description": f"Complete view of all {len(file_data)} files in your collection",
            "type": "complete",
            "filters": {},  # No filters = show all
            "sort_order": [{"field": "file_name", "direction": "asc"}],
            "display_mode": "list",
            "columns": ["file_name", "created_at", "file_type", "summary"],
            "icon": "files",
            "color": "#74B9FF",
            "is_system_view": True,
            "file_count": len(file_data)
        })
        
        # 1. Recent Files View
        default_views.append({
            "view_id": "recent_files",
            "name": "Recent Files",
            "description": "Files added or modified in the last 7 days",
            "type": "temporal",
            "filters": {
                "date_range": {
                    "field": "created_at",
                    "operation": "last_n_days",
                    "value": 7
                }
            },
            "sort_order": [{"field": "created_at", "direction": "desc"}],
            "display_mode": "list",
            "columns": ["file_name", "created_at", "file_type", "summary"],
            "icon": "clock",
            "color": "#4ECDC4",
            "is_system_view": True
        })
        
        # 2. High Priority Documents
        high_priority_files = self._identify_high_priority_files(file_data)
        if high_priority_files:
            default_views.append({
                "view_id": "high_priority",
                "name": "Important Documents",
                "description": "Documents with high relevance or frequent references",
                "type": "priority",
                "filters": {
                    "file_ids": {
                        "field": "file_id",
                        "operation": "in",
                        "value": [f["file_id"] for f in high_priority_files]
                    }
                },
                "sort_order": [{"field": "priority_score", "direction": "desc"}],
                "display_mode": "cards",
                "icon": "star",
                "color": "#FF6B6B",
                "is_system_view": True
            })
        
        # 3. By Document Type (modified for single file support)
        file_types = self._extract_file_types(file_data)
        for file_type in file_types:
            if file_types[file_type] >= 1:  # Changed from > 1 to >= 1 for single files
                default_views.append({
                    "view_id": f"type_{file_type.lower()}",
                    "name": f"{file_type.title()} Documents",
                    "description": f"All {file_type} documents",
                    "type": "category",
                    "filters": {
                        "file_type": {
                            "field": "file_type",
                            "operation": "equals",
                            "value": file_type
                        }
                    },
                    "sort_order": [{"field": "file_name", "direction": "asc"}],
                    "display_mode": "grid",
                    "icon": self._get_file_type_icon(file_type),
                    "color": self._get_file_type_color(file_type),
                    "is_system_view": True
                })
        
        # 4. Collection-based Views
        if organization_data.get("collections"):
            for collection in organization_data["collections"][:5]:  # Limit to top 5 collections
                default_views.append({
                    "view_id": f"collection_{collection['id']}",
                    "name": f"Collection: {collection['name']}",
                    "description": collection.get("description", ""),
                    "type": "collection",
                    "filters": {
                        "collection_id": {
                            "field": "collection_id",
                            "operation": "equals",
                            "value": collection["id"]
                        }
                    },
                    "sort_order": [{"field": "relevance_score", "direction": "desc"}],
                    "display_mode": "board",
                    "icon": "folder",
                    "color": collection.get("visualization", {}).get("color_scheme", "#96CEB4"),
                    "is_system_view": True,
                    "collection_metadata": collection
                })
        
        # 5. Unorganized Files View
        unorganized_files = self._identify_unorganized_files(file_data, organization_data)
        if unorganized_files:
            default_views.append({
                "view_id": "unorganized",
                "name": "Unorganized Files",
                "description": "Files that haven't been categorized or organized",
                "type": "special",
                "filters": {
                    "file_ids": {
                        "field": "file_id",
                        "operation": "in",
                        "value": [f["file_id"] for f in unorganized_files]
                    }
                },
                "sort_order": [{"field": "created_at", "direction": "desc"}],
                "display_mode": "list",
                "icon": "inbox",
                "color": "#DDA0DD",
                "is_system_view": True,
                "actions": ["organize", "tag", "move_to_collection"]
            })
        
        return default_views
    
    def _create_contextual_views(self, file_data: List[Dict[str, Any]], organization_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create contextual views based on content analysis."""
        
        contextual_views = []
        
        # Always create a comprehensive single file view for single files
        if len(file_data) == 1:
            file_info = file_data[0]
            page_count = file_info.get('page_count', 0)
            
            contextual_views.append({
                "view_id": "single_file_comprehensive",
                "name": f"Complete Analysis: {file_info.get('file_name', 'Document')}",
                "description": f"Full breakdown of this {page_count}-page document with all extracted insights",
                "type": "comprehensive_single",
                "files": [file_info['file_id']],
                "filters": {"file_type": [file_info.get('file_type', 'unknown')]},
                "sort_by": "relevance",
                "display_mode": "detailed",
                "sections": {
                    "overview": {
                        "summary": file_info.get('summary', 'No summary available'),
                        "page_count": page_count,
                        "file_type": file_info.get('file_type', 'unknown')
                    },
                    "content_analysis": {
                        "topics": file_info.get('topics', []),
                        "entities": file_info.get('entities', {}),
                        "keywords": file_info.get('keywords', [])
                    },
                    "evidence": file_info.get('evidence_items', [])
                },
                "priority": 10,
                "created_at": datetime.utcnow().isoformat()
            })
        
        # 1. Topic-based Views
        topic_clusters = self._create_topic_based_views(file_data)
        contextual_views.extend(topic_clusters)
        
        # 2. Entity-focused Views
        entity_views = self._create_entity_based_views(file_data)
        contextual_views.extend(entity_views)
        
        # 3. Time-based Views
        temporal_views = self._create_temporal_views(file_data)
        contextual_views.extend(temporal_views)
        
        # 4. Similarity-based Views
        if organization_data.get("clusters"):
            similarity_views = self._create_cluster_based_views(organization_data["clusters"])
            contextual_views.extend(similarity_views)
        
        # 5. Research Workflow Views
        workflow_views = self._create_workflow_views(file_data)
        contextual_views.extend(workflow_views)
        
        # Ensure we always have at least one contextual view
        if not contextual_views and len(file_data) == 1:
            file_info = file_data[0]
            contextual_views.append({
                "view_id": "fallback_single_file",
                "name": f"Document View: {file_info.get('file_name', 'Unnamed File')}",
                "description": "Standard view for your document",
                "type": "document_view",
                "files": [file_info['file_id']],
                "filters": {},
                "sort_by": "relevance",
                "display_mode": "standard",
                "priority": 1,
                "created_at": datetime.utcnow().isoformat()
            })
        
        log.info(f"[SavedViews] Generated {len(contextual_views)} contextual views")
        return contextual_views
    
    def _create_topic_based_views(self, file_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create views based on dominant topics."""
        
        # Collect all topics and their frequencies
        topic_counts = defaultdict(int)
        topic_files = defaultdict(list)
        
        for file_info in file_data:
            topics = file_info.get("topics", [])
            # Handle both list and dict format topics
            if isinstance(topics, list):
                topic_list = topics
            elif isinstance(topics, dict):
                topic_list = list(topics.keys()) if topics else []
            else:
                topic_list = []
                
            for topic in topic_list:
                topic_name = str(topic).strip()
                if topic_name:
                    topic_counts[topic_name] += 1
                    topic_files[topic_name].append(file_info["file_id"])
        
        # Create views for topics (supporting single files)
        topic_views = []
        for topic, count in topic_counts.items():
            if count >= 1 and topic:  # Support single files and ensure topic is not empty
                view_id = f"topic_{topic.lower().replace(' ', '_').replace('/', '_')[:50]}"
                topic_views.append({
                    "view_id": view_id,
                    "name": f"Topic: {topic.title()}",
                    "description": f"Content focused on {topic} ({count} file{'s' if count > 1 else ''})",
                    "type": "topic_focused",
                    "files": topic_files[topic],
                    "filters": {
                        "topic": {
                            "field": "topics",
                            "operation": "contains",
                            "value": topic
                        }
                    },
                    "sort_order": [{"field": "relevance_score", "direction": "desc"}],
                    "display_mode": "cards",
                    "icon": "tag",
                    "color": "#FFEAA7",
                    "metadata": {
                        "topic_name": topic,
                        "file_count": count,
                        "related_topics": self._find_related_topics(topic, topic_counts)
                    }
                })
        
        return topic_views[:10]  # Limit to top 10 topic views
    
    def _create_entity_based_views(self, file_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create views focused on specific entities."""
        
        entity_views = []
        
        # Collect entities by type
        entities_by_type = defaultdict(lambda: defaultdict(list))
        
        for file_info in file_data:
            entities = file_info.get("entities", {})
            if isinstance(entities, dict):
                for entity_type, entity_list in entities.items():
                    if isinstance(entity_list, list):
                        for entity in entity_list:
                            entity_name = str(entity).strip()
                            if entity_name:
                                entities_by_type[entity_type][entity_name].append(file_info["file_id"])
        
        # Create views for entities (supporting single files)
        for entity_type, entities in entities_by_type.items():
            for entity, file_ids in entities.items():
                if len(file_ids) >= 1 and entity:  # Support single files and ensure entity is not empty
                    view_id = f"entity_{entity.lower().replace(' ', '_').replace('/', '_')[:50]}"
                    entity_views.append({
                        "view_id": view_id,
                        "name": f"{entity_type.title()}: {entity}",
                        "description": f"Content featuring {entity} ({len(file_ids)} file{'s' if len(file_ids) > 1 else ''})",
                        "type": "entity_focused",
                        "files": file_ids,
                        "filters": {
                            "entity": {
                                "field": f"entities.{entity_type}",
                                "operation": "contains",
                                "value": entity
                            }
                        },
                        "sort_order": [{"field": "entity_relevance", "direction": "desc"}],
                        "display_mode": "list",
                        "icon": self._get_entity_icon(entity_type),
                        "color": self._get_entity_color(entity_type),
                        "metadata": {
                            "entity_name": entity,
                            "entity_type": entity_type,
                            "file_count": len(file_ids)
                        }
                    })
        
        return entity_views[:8]  # Limit to top 8 entity views
    
    def _create_temporal_views(self, file_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create time-based views."""
        
        temporal_views = [
            {
                "view_id": "this_week",
                "name": "This Week",
                "description": "Files from the current week",
                "type": "temporal",
                "filters": {
                    "date_range": {
                        "field": "created_at",
                        "operation": "current_week",
                        "value": None
                    }
                },
                "sort_order": [{"field": "created_at", "direction": "desc"}],
                "display_mode": "timeline",
                "icon": "calendar-week",
                "color": "#45B7D1"
            },
            {
                "view_id": "this_month",
                "name": "This Month",
                "description": "Files from the current month",
                "type": "temporal",
                "filters": {
                    "date_range": {
                        "field": "created_at",
                        "operation": "current_month",
                        "value": None
                    }
                },
                "sort_order": [{"field": "created_at", "direction": "desc"}],
                "display_mode": "calendar",
                "icon": "calendar",
                "color": "#96CEB4"
            }
        ]
        
        return temporal_views
    
    def _create_cluster_based_views(self, clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create views based on document clusters."""
        
        cluster_views = []
        
        for cluster in clusters[:5]:  # Limit to top 5 clusters
            file_ids = [file_detail["file_id"] for file_detail in cluster.get("file_details", [])]
            
            cluster_views.append({
                "view_id": f"cluster_{cluster.get('cluster_id', 'unknown')}",
                "name": f"Cluster: {cluster.get('name', 'Similar Documents')}",
                "description": cluster.get("description", "Automatically grouped similar documents"),
                "type": "cluster",
                "filters": {
                    "file_ids": {
                        "field": "file_id",
                        "operation": "in",
                        "value": file_ids
                    }
                },
                "sort_order": [{"field": "similarity_score", "direction": "desc"}],
                "display_mode": "cluster",
                "icon": "sitemap",
                "color": "#98D8C8",
                "metadata": {
                    "cluster_quality": cluster.get("quality_score", 0),
                    "cluster_size": len(file_ids),
                    "common_topics": cluster.get("characteristics", {}).get("common_topics", [])
                }
            })
        
        return cluster_views
    
    def _create_workflow_views(self, file_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create views for common research workflows."""
        
        workflow_views = [
            {
                "view_id": "to_review",
                "name": "To Review",
                "description": "Documents requiring review or analysis",
                "type": "workflow",
                "filters": {
                    "status": {
                        "field": "review_status",
                        "operation": "in",
                        "value": ["pending", "in_progress", None]
                    }
                },
                "sort_order": [{"field": "priority", "direction": "desc"}],
                "display_mode": "kanban",
                "icon": "eye",
                "color": "#FF9F43",
                "actions": ["mark_reviewed", "add_notes", "set_priority"]
            },
            {
                "view_id": "research_sources",
                "name": "Research Sources", 
                "description": "Primary sources and reference materials",
                "type": "workflow",
                "filters": {
                    "document_type": {
                        "field": "document_category",
                        "operation": "in",
                        "value": ["academic", "research", "reference", "primary_source"]
                    }
                },
                "sort_order": [{"field": "citation_count", "direction": "desc"}],
                "display_mode": "bibliography",
                "icon": "book",
                "color": "#6C5CE7"
            },
            {
                "view_id": "evidence_documents",
                "name": "Evidence & Data",
                "description": "Documents containing evidence, data, and supporting materials",
                "type": "workflow",
                "filters": {
                    "has_evidence": {
                        "field": "evidence_count",
                        "operation": "greater_than",
                        "value": 0
                    }
                },
                "sort_order": [{"field": "evidence_count", "direction": "desc"}],
                "display_mode": "evidence_board",
                "icon": "chart-line",
                "color": "#00B894"
            }
        ]
        
        return workflow_views
    
    def _build_filter_combinations(self, file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build intelligent filter combinations."""
        
        # Analyze available filter dimensions
        available_filters = self._analyze_filter_dimensions(file_data)
        
        # Create smart filter combinations
        filter_combinations = {
            "quick_filters": [
                {"name": "PDF Documents", "filter": {"file_type": "pdf"}},
                {"name": "Recent (7 days)", "filter": {"date_range": "last_7_days"}},
                {"name": "Has Evidence", "filter": {"evidence_count": ">0"}},
                {"name": "Multiple Topics", "filter": {"topic_count": ">1"}}
            ],
            "advanced_combinations": [
                {
                    "name": "Recent Research Papers",
                    "filters": [
                        {"field": "file_type", "operation": "equals", "value": "pdf"},
                        {"field": "created_at", "operation": "last_n_days", "value": 14},
                        {"field": "topics", "operation": "contains_any", "value": ["research", "study", "analysis"]}
                    ]
                },
                {
                    "name": "Evidence-Rich Documents",
                    "filters": [
                        {"field": "evidence_count", "operation": "greater_than", "value": 5},
                        {"field": "file_size", "operation": "greater_than", "value": 10000}
                    ]
                }
            ],
            "saved_searches": [],
            "filter_suggestions": self._generate_filter_suggestions(available_filters)
        }
        
        return filter_combinations
    
    def _create_view_templates(self) -> List[Dict[str, Any]]:
        """Create reusable view templates."""
        
        templates = [
            {
                "template_id": "research_project",
                "name": "Research Project Template",
                "description": "Standard views for research projects",
                "views": [
                    {"name": "Literature Review", "type": "academic", "focus": "sources"},
                    {"name": "Data Collection", "type": "workflow", "focus": "evidence"},
                    {"name": "Analysis Notes", "type": "personal", "focus": "annotations"},
                    {"name": "Final Report", "type": "deliverable", "focus": "synthesis"}
                ]
            },
            {
                "template_id": "content_analysis",
                "name": "Content Analysis Template",
                "description": "Views for systematic content analysis",
                "views": [
                    {"name": "Raw Materials", "type": "source", "focus": "unprocessed"},
                    {"name": "Coded Content", "type": "analysis", "focus": "categorized"},
                    {"name": "Themes & Patterns", "type": "synthesis", "focus": "insights"},
                    {"name": "Quality Check", "type": "validation", "focus": "accuracy"}
                ]
            },
            {
                "template_id": "document_review",
                "name": "Document Review Template",
                "description": "Views for document review workflows",
                "views": [
                    {"name": "To Review", "type": "queue", "focus": "pending"},
                    {"name": "In Progress", "type": "active", "focus": "current"},
                    {"name": "Completed", "type": "archive", "focus": "finished"},
                    {"name": "Flagged Issues", "type": "attention", "focus": "problems"}
                ]
            }
        ]
        
        return templates
    
    def _create_management_features(self, all_views: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create view management features."""
        
        return {
            "view_organization": {
                "categories": ["system", "topic", "entity", "temporal", "cluster", "workflow"],
                "favorites": [],
                "recently_used": [],
                "custom_folders": []
            },
            "sharing_options": {
                "export_formats": ["json", "csv", "bookmark"],
                "share_permissions": ["view", "edit", "admin"],
                "collaboration_features": ["comments", "annotations", "shared_filters"]
            },
            "automation": {
                "auto_update": True,
                "smart_notifications": ["new_matches", "view_changes", "collaboration_updates"],
                "scheduled_refreshes": ["daily", "weekly", "monthly"]
            },
            "customization": {
                "layout_options": ["list", "grid", "cards", "timeline", "kanban", "board"],
                "sort_options": self._generate_sort_options(all_views),
                "display_fields": self._generate_display_fields(),
                "color_themes": ["default", "dark", "high_contrast", "custom"]
            },
            "performance": {
                "lazy_loading": True,
                "pagination": {"default_size": 20, "max_size": 100},
                "caching": {"enabled": True, "ttl": 300},
                "search_optimization": True
            }
        }
    
    def _create_analytics_framework(self) -> Dict[str, Any]:
        """Create analytics framework for view usage."""
        
        return {
            "usage_tracking": {
                "view_access_frequency": {},
                "time_spent_per_view": {},
                "most_used_filters": {},
                "search_patterns": {}
            },
            "optimization_suggestions": {
                "unused_views": [],
                "popular_filter_combinations": [],
                "performance_improvements": [],
                "new_view_recommendations": []
            },
            "reporting": {
                "daily_summary": True,
                "weekly_insights": True,
                "trend_analysis": True,
                "efficiency_metrics": True
            }
        }
    
    # Helper methods
    def _identify_high_priority_files(self, file_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify files that should be prioritized."""
        high_priority = []
        
        for file_info in file_data:
            priority_score = 0
            
            # High evidence count
            evidence_count = len(file_info.get("evidence_items", []))
            if evidence_count > 5:
                priority_score += 2
            
            # Multiple topics
            topic_count = len(file_info.get("topics", []))
            if topic_count > 3:
                priority_score += 1
            
            # Recent file
            # (Would check file creation date in real implementation)
            priority_score += 1
            
            if priority_score >= 3:
                file_info["priority_score"] = priority_score
                high_priority.append(file_info)
        
        return sorted(high_priority, key=lambda x: x["priority_score"], reverse=True)[:10]
    
    def _extract_file_types(self, file_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Extract file types and their counts."""
        file_types = defaultdict(int)
        
        for file_info in file_data:
            file_name = file_info.get("file_name", "")
            if "." in file_name:
                extension = file_name.split(".")[-1].lower()
                file_types[extension] += 1
            else:
                file_types["unknown"] += 1
        
        return dict(file_types)
    
    def _identify_unorganized_files(self, file_data: List[Dict[str, Any]], organization_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify files that haven't been organized."""
        organized_file_ids = set()
        
        # Get file IDs from collections
        if organization_data.get("collections"):
            for collection in organization_data["collections"]:
                for file_detail in collection.get("file_details", []):
                    organized_file_ids.add(file_detail["file_id"])
        
        # Get file IDs from clusters
        if organization_data.get("clusters"):
            for cluster in organization_data["clusters"]:
                for file_detail in cluster.get("file_details", []):
                    organized_file_ids.add(file_detail["file_id"])
        
        # Find unorganized files
        unorganized = []
        for file_info in file_data:
            if file_info["file_id"] not in organized_file_ids:
                unorganized.append(file_info)
        
        return unorganized
    
    def _find_related_topics(self, topic: str, topic_counts: Dict[str, int]) -> List[str]:
        """Find topics related to the given topic."""
        # Simple word-based similarity
        related = []
        topic_words = set(topic.lower().split())
        
        for other_topic, count in topic_counts.items():
            if other_topic != topic and count >= 2:
                other_words = set(other_topic.lower().split())
                if topic_words.intersection(other_words):
                    related.append(other_topic)
        
        return related[:3]  # Limit to 3 related topics
    
    def _get_file_type_icon(self, file_type: str) -> str:
        """Get icon for file type."""
        icon_mapping = {
            "pdf": "file-pdf",
            "doc": "file-word",
            "docx": "file-word", 
            "txt": "file-text",
            "xlsx": "file-excel",
            "pptx": "file-powerpoint",
            "jpg": "file-image",
            "png": "file-image"
        }
        return icon_mapping.get(file_type, "file")
    
    def _get_file_type_color(self, file_type: str) -> str:
        """Get color for file type."""
        color_mapping = {
            "pdf": "#FF6B6B",
            "doc": "#4ECDC4",
            "docx": "#4ECDC4",
            "txt": "#45B7D1",
            "xlsx": "#96CEB4",
            "pptx": "#FFEAA7"
        }
        return color_mapping.get(file_type, "#DDA0DD")
    
    def _get_entity_icon(self, entity_type: str) -> str:
        """Get icon for entity type."""
        icon_mapping = {
            "person": "user",
            "organization": "building",
            "location": "map-marker",
            "product": "box"
        }
        return icon_mapping.get(entity_type, "tag")
    
    def _get_entity_color(self, entity_type: str) -> str:
        """Get color for entity type."""
        color_mapping = {
            "person": "#FF6B6B",
            "organization": "#4ECDC4",
            "location": "#45B7D1",
            "product": "#96CEB4"
        }
        return color_mapping.get(entity_type, "#DDA0DD")
    
    def _analyze_filter_dimensions(self, file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze available dimensions for filtering."""
        dimensions = {
            "file_types": set(),
            "topics": set(),
            "entity_types": set(),
            "date_ranges": [],
            "file_sizes": [],
            "evidence_counts": []
        }
        
        for file_info in file_data:
            # File types
            file_name = file_info.get("file_name", "")
            if "." in file_name:
                dimensions["file_types"].add(file_name.split(".")[-1].lower())
            
            # Topics
            dimensions["topics"].update(file_info.get("topics", []))
            
            # Entity types
            if file_info.get("entities"):
                dimensions["entity_types"].update(file_info["entities"].keys())
            
            # Evidence counts
            evidence_count = len(file_info.get("evidence_items", []))
            dimensions["evidence_counts"].append(evidence_count)
        
        # Convert sets to lists for JSON serialization
        dimensions["file_types"] = list(dimensions["file_types"])
        dimensions["topics"] = list(dimensions["topics"])
        dimensions["entity_types"] = list(dimensions["entity_types"])
        
        return dimensions
    
    def _generate_filter_suggestions(self, available_filters: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate intelligent filter suggestions."""
        suggestions = []
        
        # Suggest popular file type filters
        if available_filters["file_types"]:
            for file_type in available_filters["file_types"][:3]:
                suggestions.append({
                    "type": "file_type",
                    "label": f"Show only {file_type.upper()} files",
                    "filter": {"file_type": file_type}
                })
        
        # Suggest topic filters
        if available_filters["topics"]:
            popular_topics = available_filters["topics"][:5]
            for topic in popular_topics:
                suggestions.append({
                    "type": "topic",
                    "label": f"Focus on {topic}",
                    "filter": {"topics": {"contains": topic}}
                })
        
        return suggestions
    
    def _generate_sort_options(self, all_views: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Generate available sort options."""
        return [
            {"field": "created_at", "label": "Date Created", "direction": "desc"},
            {"field": "modified_at", "label": "Date Modified", "direction": "desc"},
            {"field": "file_name", "label": "Name", "direction": "asc"},
            {"field": "file_size", "label": "File Size", "direction": "desc"},
            {"field": "relevance_score", "label": "Relevance", "direction": "desc"},
            {"field": "evidence_count", "label": "Evidence Count", "direction": "desc"},
            {"field": "topic_count", "label": "Topic Count", "direction": "desc"}
        ]
    
    def _generate_display_fields(self) -> List[Dict[str, str]]:
        """Generate available display fields."""
        return [
            {"field": "file_name", "label": "File Name", "type": "text", "default": True},
            {"field": "summary", "label": "Summary", "type": "text", "default": True},
            {"field": "created_at", "label": "Created", "type": "date", "default": True},
            {"field": "file_type", "label": "Type", "type": "badge", "default": True},
            {"field": "topics", "label": "Topics", "type": "tags", "default": False},
            {"field": "evidence_count", "label": "Evidence", "type": "number", "default": False},
            {"field": "entities", "label": "Entities", "type": "tags", "default": False},
            {"field": "file_size", "label": "Size", "type": "size", "default": False}
        ]
