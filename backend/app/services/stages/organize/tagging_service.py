# app/services/stages/organize/tagging_service.py
import logging
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
from datetime import datetime
from app.services.ai_service_base import AIServiceBase

log = logging.getLogger(__name__)

class TaggingService(AIServiceBase):
    """
    Service for auto-generating and managing hierarchical tag taxonomies.
    Creates intelligent tagging systems based on content analysis.
    """
    
    def __init__(self):
        super().__init__()
        self.service_name = "tag_taxonomy_manager"
        
    def get_service_info(self) -> Dict[str, Any]:
        """
        Return information about the tagging service.
        
        Returns:
            Dictionary with service information
        """
        return {
            "service_name": self.service_name,
            "description": "Service for auto-generating and managing hierarchical tag taxonomies",
            "capabilities": [
                "hierarchical_tagging",
                "tag_taxonomy_creation",
                "intelligent_categorization",
                "tag_relationship_mapping"
            ],
            "supported_types": ["topic_tags", "content_tags", "meta_tags", "hierarchical"],
            "version": "1.0.0"
        }
        
    def build_tag_taxonomy(self, file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a comprehensive tag taxonomy from document analysis.
        
        Args:
            file_data: List of file analysis data with entities, topics, etc.
            
        Returns:
            Dict containing hierarchical tag taxonomy and metadata
        """
        try:
            log.info(f"[Tagging] Building taxonomy for {len(file_data)} files")
            
            # 1. Extract all potential tags from content
            raw_tags = self._extract_raw_tags(file_data)
            
            # 2. Clean and normalize tags
            normalized_tags = self._normalize_tags(raw_tags)
            
            # 3. Build hierarchical taxonomy
            taxonomy = self._build_hierarchy(normalized_tags, file_data)
            
            # 4. Add semantic relationships
            enriched_taxonomy = self._add_semantic_relationships(taxonomy)
            
            # 5. Generate tag suggestions and auto-tagging rules
            tagging_rules = self._generate_tagging_rules(enriched_taxonomy, file_data)
            
            result = {
                "taxonomy": enriched_taxonomy,
                "tagging_rules": tagging_rules,
                "tag_statistics": self._generate_tag_statistics(enriched_taxonomy, file_data),
                "suggested_tags": self._suggest_additional_tags(enriched_taxonomy),
                "created_at": datetime.utcnow().isoformat()
            }
            
            log.info(f"[Tagging] Created taxonomy with {len(enriched_taxonomy)} top-level categories")
            return result
            
        except Exception as e:
            log.error(f"[Tagging] Error building taxonomy: {e}")
            raise
    
    def _extract_raw_tags(self, file_data: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract all potential tags from various sources."""
        raw_tags = {
            "entities": [],
            "topics": [],
            "keywords": [],
            "concepts": [],
            "categories": []
        }
        
        for file_info in file_data:
            # Extract from entities
            if file_info.get("entities"):
                for entity_type, entities in file_info["entities"].items():
                    if isinstance(entities, list):
                        for entity in entities:
                            if isinstance(entity, str):
                                raw_tags["entities"].append(entity.lower())
                            elif isinstance(entity, dict):
                                # If entity is a dict, try to get text/name field
                                entity_text = entity.get('text') or entity.get('name') or entity.get('entity') or str(entity)
                                raw_tags["entities"].append(entity_text.lower())
                            else:
                                raw_tags["entities"].append(str(entity).lower())
            
            # Extract from topics
            if file_info.get("topics"):
                for topic in file_info["topics"]:
                    if isinstance(topic, str):
                        raw_tags["topics"].append(topic.lower())
                    else:
                        raw_tags["topics"].append(str(topic).lower())
            
            # Extract from summary keywords
            if file_info.get("summary"):
                keywords = self._extract_keywords_from_text(file_info["summary"])
                raw_tags["keywords"].extend(keywords)
            
            # Extract from document analysis
            if file_info.get("key_points"):
                for point in file_info["key_points"]:
                    if isinstance(point, dict) and "text" in point:
                        concepts = self._extract_concepts_from_text(point["text"])
                        raw_tags["concepts"].extend(concepts)
        
        return raw_tags
    
    def _normalize_tags(self, raw_tags: Dict[str, List[str]]) -> Dict[str, List[Dict[str, Any]]]:
        """Clean, normalize, and rank tags."""
        normalized = {}
        
        for tag_type, tags in raw_tags.items():
            # Remove duplicates and count frequencies
            tag_counts = defaultdict(int)
            for tag in tags:
                cleaned_tag = self._clean_tag(tag)
                if cleaned_tag and len(cleaned_tag) > 2:  # Filter very short tags
                    tag_counts[cleaned_tag] += 1
            
            # Convert to structured format with metadata
            normalized[tag_type] = [
                {
                    "name": tag,
                    "frequency": count,
                    "confidence": min(count / len(tags) * 10, 1.0) if tags else 0,
                    "type": tag_type,
                    "variants": self._find_tag_variants(tag, tags)
                }
                for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
                if count > 1  # Only include tags that appear more than once
            ]
        
        return normalized
    
    def _build_hierarchy(self, normalized_tags: Dict[str, List[Dict[str, Any]]], file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build hierarchical taxonomy structure."""
        
        # Create main taxonomy categories
        taxonomy = {
            "content_types": {
                "name": "Content Types",
                "description": "Document types and formats",
                "children": {},
                "tags": []
            },
            "subject_areas": {
                "name": "Subject Areas",
                "description": "Academic and professional domains",
                "children": {},
                "tags": []
            },
            "entities": {
                "name": "Named Entities",
                "description": "People, places, organizations",
                "children": {
                    "people": {"name": "People", "tags": []},
                    "organizations": {"name": "Organizations", "tags": []},
                    "locations": {"name": "Locations", "tags": []},
                    "products": {"name": "Products", "tags": []}
                },
                "tags": []
            },
            "concepts": {
                "name": "Key Concepts",
                "description": "Important ideas and themes",
                "children": {},
                "tags": []
            },
            "temporal": {
                "name": "Time-based",
                "description": "Time periods and chronological markers",
                "children": {
                    "periods": {"name": "Time Periods", "tags": []},
                    "events": {"name": "Events", "tags": []}
                },
                "tags": []
            }
        }
        
        # Populate taxonomy with normalized tags
        for tag_type, tags in normalized_tags.items():
            for tag in tags:
                self._assign_tag_to_hierarchy(tag, taxonomy, file_data)
        
        # Use AI to enhance hierarchy structure
        enhanced_taxonomy = self._ai_enhance_hierarchy(taxonomy)
        
        return enhanced_taxonomy
    
    def _assign_tag_to_hierarchy(self, tag: Dict[str, Any], taxonomy: Dict[str, Any], file_data: List[Dict[str, Any]]):
        """Assign a tag to the appropriate place in the hierarchy."""
        tag_name = tag["name"]
        tag_type = tag["type"]
        
        # Assign based on tag type
        if tag_type == "entities":
            # Try to categorize entity type
            entity_category = self._classify_entity(tag_name)
            if entity_category in taxonomy["entities"]["children"]:
                taxonomy["entities"]["children"][entity_category]["tags"].append(tag)
            else:
                taxonomy["entities"]["tags"].append(tag)
                
        elif tag_type == "topics":
            # Assign to subject areas
            subject_category = self._classify_subject_area(tag_name)
            if subject_category:
                if subject_category not in taxonomy["subject_areas"]["children"]:
                    taxonomy["subject_areas"]["children"][subject_category] = {
                        "name": subject_category.title(),
                        "tags": []
                    }
                taxonomy["subject_areas"]["children"][subject_category]["tags"].append(tag)
            else:
                taxonomy["subject_areas"]["tags"].append(tag)
                
        elif tag_type == "concepts":
            taxonomy["concepts"]["tags"].append(tag)
            
        else:
            # Default assignment based on content analysis
            category = self._determine_best_category(tag_name, taxonomy)
            taxonomy[category]["tags"].append(tag)
    
    def _ai_enhance_hierarchy(self, taxonomy: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to enhance and validate the hierarchy structure."""
        try:
            # Prepare taxonomy for AI analysis
            taxonomy_summary = self._summarize_taxonomy(taxonomy)
            
            enhancement_prompt = f"""
            Analyze this tag taxonomy and suggest improvements to the hierarchical structure.
            
            Current Taxonomy:
            {taxonomy_summary}
            
            Please suggest:
            1. Better hierarchical groupings
            2. Missing categories that would be useful
            3. Tags that should be moved to different categories
            4. Subcategories that should be created
            
            Return suggestions as JSON:
            {{
                "suggested_moves": [
                    {{"tag": "tag_name", "from": "current_category", "to": "suggested_category", "reason": "explanation"}}
                ],
                "new_categories": [
                    {{"name": "category_name", "description": "purpose", "parent": "parent_category"}}
                ],
                "consolidations": [
                    {{"merge": ["category1", "category2"], "into": "new_category_name", "reason": "explanation"}}
                ]
            }}
            """
            
            response = self._call_openai_api(enhancement_prompt, max_tokens=1000)
            suggestions = self._parse_json_response(response)
            
            # Apply AI suggestions to enhance taxonomy
            enhanced_taxonomy = self._apply_ai_suggestions(taxonomy, suggestions)
            return enhanced_taxonomy
            
        except Exception as e:
            log.warning(f"[Tagging] AI enhancement failed: {e}, using original taxonomy")
            return taxonomy
    
    def _add_semantic_relationships(self, taxonomy: Dict[str, Any]) -> Dict[str, Any]:
        """Add semantic relationships between tags."""
        enriched = taxonomy.copy()
        
        # Add relationships to each category
        for category_name, category in enriched.items():
            if isinstance(category, dict) and "tags" in category:
                # Find related tags within category
                category["relationships"] = self._find_tag_relationships(category["tags"])
                
                # Add category-level metadata
                category["metadata"] = {
                    "total_tags": len(category["tags"]),
                    "avg_confidence": self._calculate_avg_confidence(category["tags"]),
                    "most_frequent_tags": sorted(category["tags"], key=lambda x: x["frequency"], reverse=True)[:5],
                    "last_updated": datetime.utcnow().isoformat()
                }
        
        return enriched
    
    def _generate_tagging_rules(self, taxonomy: Dict[str, Any], file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate automatic tagging rules based on the taxonomy."""
        return {
            "auto_tag_rules": [
                {
                    "rule_id": f"rule_{i}",
                    "condition": self._create_tagging_condition(tag),
                    "tag_assignment": tag["name"],
                    "confidence_threshold": 0.7,
                    "category": category_name
                }
                for category_name, category in taxonomy.items()
                if isinstance(category, dict) and "tags" in category
                for i, tag in enumerate(category["tags"][:5])  # Top 5 tags per category
            ],
            "manual_review_rules": self._create_manual_review_rules(taxonomy),
            "tag_validation_rules": self._create_validation_rules(taxonomy)
        }
    
    def _generate_tag_statistics(self, taxonomy: Dict[str, Any], file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive statistics about the tag taxonomy."""
        total_tags = 0
        total_categories = 0
        tag_distribution = {}
        
        for category_name, category in taxonomy.items():
            if isinstance(category, dict):
                total_categories += 1
                if "tags" in category:
                    category_tag_count = len(category["tags"])
                    total_tags += category_tag_count
                    tag_distribution[category_name] = category_tag_count
        
        return {
            "total_tags": total_tags,
            "total_categories": total_categories,
            "tag_distribution": tag_distribution,
            "coverage_metrics": {
                "files_fully_tagged": len([f for f in file_data if self._is_file_well_tagged(f, taxonomy)]),
                "avg_tags_per_file": total_tags / len(file_data) if file_data else 0,
                "tag_diversity": len(set([tag["name"] for cat in taxonomy.values() if isinstance(cat, dict) and "tags" in cat for tag in cat["tags"]]))
            },
            "quality_metrics": {
                "avg_tag_confidence": self._calculate_overall_confidence(taxonomy),
                "taxonomy_completeness": self._assess_taxonomy_completeness(taxonomy),
                "consistency_score": self._calculate_consistency_score(taxonomy)
            }
        }
    
    def _suggest_additional_tags(self, taxonomy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest additional tags that might be useful."""
        suggestions = []
        
        # Analyze gaps in taxonomy
        for category_name, category in taxonomy.items():
            if isinstance(category, dict) and "tags" in category:
                if len(category["tags"]) < 3:
                    suggestions.append({
                        "type": "expand_category",
                        "category": category_name,
                        "reason": f"Category '{category_name}' has few tags, consider adding more",
                        "suggested_tags": self._suggest_tags_for_category(category_name)
                    })
        
        return suggestions
    
    # Helper methods
    def _clean_tag(self, tag: str) -> str:
        """Clean and normalize a tag string."""
        if not tag:
            return ""
        
        # Remove special characters, normalize case
        cleaned = tag.lower().strip()
        cleaned = ''.join(c for c in cleaned if c.isalnum() or c.isspace())
        cleaned = ' '.join(cleaned.split())  # Normalize whitespace
        
        return cleaned
    
    def _find_tag_variants(self, tag: str, all_tags: List[str]) -> List[str]:
        """Find similar variants of a tag."""
        variants = []
        tag_lower = tag.lower()
        
        for other_tag in all_tags:
            other_lower = other_tag.lower()
            if other_lower != tag_lower and (tag_lower in other_lower or other_lower in tag_lower):
                variants.append(other_tag)
        
        return variants[:3]  # Limit to 3 variants
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract keywords from text content."""
        # Simple keyword extraction (can be enhanced with NLP)
        words = text.lower().split()
        # Filter out common words and keep meaningful terms
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        keywords = [word.strip('.,!?;:') for word in words if len(word) > 3 and word not in stop_words]
        return keywords[:10]  # Limit to 10 keywords
    
    def _extract_concepts_from_text(self, text: str) -> List[str]:
        """Extract key concepts from text."""
        # Simple concept extraction
        sentences = text.split('.')
        concepts = []
        for sentence in sentences:
            if len(sentence.strip()) > 20:  # Meaningful sentences
                words = sentence.strip().split()
                if len(words) >= 2:
                    concepts.append(' '.join(words[:3]))  # First 3 words as concept
        return concepts[:5]
    
    def _classify_entity(self, entity_name: str) -> str:
        """Classify an entity into a type category."""
        entity_lower = entity_name.lower()
        
        # Simple classification based on common patterns
        if any(word in entity_lower for word in ['inc', 'corp', 'ltd', 'company', 'organization']):
            return "organizations"
        elif any(word in entity_lower for word in ['dr', 'mr', 'ms', 'prof', 'john', 'mary', 'david']):
            return "people"
        elif any(word in entity_lower for word in ['city', 'country', 'street', 'building']):
            return "locations"
        else:
            return "products"  # Default
    
    def _classify_subject_area(self, topic: str) -> Optional[str]:
        """Classify a topic into a subject area."""
        topic_lower = topic.lower()
        
        subject_mapping = {
            'technology': ['tech', 'software', 'computer', 'digital', 'ai', 'machine learning'],
            'business': ['business', 'finance', 'marketing', 'strategy', 'revenue'],
            'science': ['research', 'study', 'analysis', 'experiment', 'data'],
            'education': ['education', 'learning', 'teaching', 'academic', 'student']
        }
        
        for subject, keywords in subject_mapping.items():
            if any(keyword in topic_lower for keyword in keywords):
                return subject
        
        return None
    
    def _determine_best_category(self, tag_name: str, taxonomy: Dict[str, Any]) -> str:
        """Determine the best category for a tag."""
        # Simple heuristic - can be enhanced
        tag_lower = tag_name.lower()
        
        if any(word in tag_lower for word in ['concept', 'idea', 'theory']):
            return "concepts"
        elif any(word in tag_lower for word in ['type', 'format', 'document']):
            return "content_types"
        else:
            return "concepts"  # Default
    
    def _summarize_taxonomy(self, taxonomy: Dict[str, Any]) -> str:
        """Create a summary of the taxonomy for AI analysis."""
        summary_parts = []
        
        for category_name, category in taxonomy.items():
            if isinstance(category, dict):
                tag_count = len(category.get("tags", []))
                summary_parts.append(f"{category_name}: {tag_count} tags")
                
                if "children" in category:
                    for child_name, child in category["children"].items():
                        child_tag_count = len(child.get("tags", []))
                        summary_parts.append(f"  - {child_name}: {child_tag_count} tags")
        
        return "\n".join(summary_parts)
    
    def _apply_ai_suggestions(self, taxonomy: Dict[str, Any], suggestions: Dict[str, Any]) -> Dict[str, Any]:
        """Apply AI suggestions to improve the taxonomy."""
        # This would implement the AI suggestions
        # For now, return the original taxonomy
        return taxonomy
    
    def _find_tag_relationships(self, tags: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Find semantic relationships between tags."""
        return {
            "similar_tags": [],
            "related_concepts": [],
            "hierarchical_parents": [],
            "hierarchical_children": []
        }
    
    def _calculate_avg_confidence(self, tags: List[Dict[str, Any]]) -> float:
        """Calculate average confidence score for tags."""
        if not tags:
            return 0.0
        return sum(tag.get("confidence", 0) for tag in tags) / len(tags)
    
    def _create_tagging_condition(self, tag: Dict[str, Any]) -> Dict[str, Any]:
        """Create a condition for automatic tagging."""
        return {
            "type": "keyword_match",
            "keywords": [tag["name"]] + tag.get("variants", []),
            "field": "content",
            "match_type": "contains"
        }
    
    def _create_manual_review_rules(self, taxonomy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create rules for manual review."""
        return [
            {
                "rule": "Low confidence tags require review",
                "condition": "confidence < 0.5",
                "action": "flag_for_review"
            }
        ]
    
    def _create_validation_rules(self, taxonomy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create tag validation rules."""
        return [
            {
                "rule": "Minimum tag length",
                "condition": "len(tag) >= 3",
                "error_message": "Tags must be at least 3 characters long"
            }
        ]
    
    def _is_file_well_tagged(self, file_info: Dict[str, Any], taxonomy: Dict[str, Any]) -> bool:
        """Check if a file is well-tagged according to the taxonomy."""
        # Simple check - can be enhanced
        return len(file_info.get("topics", [])) >= 3
    
    def _calculate_overall_confidence(self, taxonomy: Dict[str, Any]) -> float:
        """Calculate overall confidence score for the taxonomy."""
        all_tags = []
        for category in taxonomy.values():
            if isinstance(category, dict) and "tags" in category:
                all_tags.extend(category["tags"])
        
        return self._calculate_avg_confidence(all_tags)
    
    def _assess_taxonomy_completeness(self, taxonomy: Dict[str, Any]) -> float:
        """Assess how complete the taxonomy is."""
        # Simple completeness metric
        total_categories = len(taxonomy)
        populated_categories = sum(1 for cat in taxonomy.values() 
                                 if isinstance(cat, dict) and len(cat.get("tags", [])) > 0)
        
        return populated_categories / total_categories if total_categories > 0 else 0.0
    
    def _calculate_consistency_score(self, taxonomy: Dict[str, Any]) -> float:
        """Calculate consistency score for the taxonomy."""
        # Simple consistency check based on tag distribution
        tag_counts = []
        for category in taxonomy.values():
            if isinstance(category, dict) and "tags" in category:
                tag_counts.append(len(category["tags"]))
        
        if not tag_counts:
            return 0.0
        
        # Higher consistency if tag counts are similar across categories
        avg_count = sum(tag_counts) / len(tag_counts)
        variance = sum((count - avg_count) ** 2 for count in tag_counts) / len(tag_counts)
        
        # Normalize to 0-1 scale (lower variance = higher consistency)
        return max(0, 1 - (variance / (avg_count ** 2))) if avg_count > 0 else 0.0
    
    def _suggest_tags_for_category(self, category_name: str) -> List[str]:
        """Suggest additional tags for a category."""
        suggestions = {
            "content_types": ["report", "presentation", "manual", "guide", "specification"],
            "subject_areas": ["technology", "business", "science", "humanities", "arts"],
            "entities": ["person", "organization", "location", "product", "event"],
            "concepts": ["strategy", "implementation", "analysis", "evaluation", "planning"]
        }
        
        return suggestions.get(category_name, ["additional", "supplementary", "related"])
