# app/services/stages/organize/concept_graph_service.py
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict, Counter
from datetime import datetime
import re
from app.services.ai_service_base import AIServiceBase

log = logging.getLogger(__name__)

class ConceptGraphService(AIServiceBase):
    """
    Service for building visual knowledge graphs and concept maps from document analysis.
    Creates interactive concept networks showing relationships between ideas, entities, and topics.
    """
    
    def __init__(self):
        super().__init__()
        self.service_name = "concept_graph"
        
    def get_service_info(self) -> Dict[str, Any]:
        """
        Return information about the concept graph service.
        
        Returns:
            Dictionary with service information
        """
        return {
            "service_name": self.service_name,
            "description": "Service for building visual knowledge graphs and concept maps from document analysis",
            "capabilities": [
                "concept_mapping",
                "knowledge_graph_creation",
                "relationship_extraction",
                "interactive_visualization"
            ],
            "supported_formats": ["nodes_edges", "graph_json", "visualization_data"],
            "version": "1.0.0"
        }
        
    def build_concept_graph(self, file_data: List[Dict[str, Any]], graph_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build a comprehensive concept graph from document analysis.
        
        Args:
            file_data: List of file analysis data with entities, relationships, etc.
            graph_config: Optional configuration for graph building
            
        Returns:
            Dict containing concept graph structure and metadata
        """
        try:
            log.info(f"[ConceptGraph] Building graph for {len(file_data)} files")
            
            # Default configuration
            config = graph_config or {
                "max_nodes": 100,
                "min_edge_weight": 0.1,
                "include_entities": True,
                "include_topics": True,
                "include_concepts": True,
                "layout": "force_directed"
            }
            
            # 1. Extract all concepts, entities, and relationships
            graph_elements = self._extract_graph_elements(file_data, config)
            
            # 2. Build nodes and edges
            nodes = self._build_graph_nodes(graph_elements, config)
            edges = self._build_graph_edges(graph_elements, nodes, config)
            
            # 3. Apply graph algorithms for layout and analysis
            graph_analysis = self._analyze_graph_structure(nodes, edges)
            
            # 4. Generate concept hierarchies
            hierarchies = self._build_concept_hierarchies(nodes, edges)
            
            # 5. Create interactive features
            interactive_features = self._create_interactive_features(nodes, edges, file_data)
            
            # 6. Generate insights and recommendations
            insights = self._generate_graph_insights(nodes, edges, graph_analysis)
            
            result = {
                "graph": {
                    "nodes": nodes,
                    "edges": edges,
                    "layout": config["layout"],
                    "metadata": {
                        "total_nodes": len(nodes),
                        "total_edges": len(edges),
                        "density": len(edges) / (len(nodes) * (len(nodes) - 1) / 2) if len(nodes) > 1 else 0
                    }
                },
                "hierarchies": hierarchies,
                "analysis": graph_analysis,
                "interactive_features": interactive_features,
                "insights": insights,
                "configuration": config,
                "created_at": datetime.utcnow().isoformat()
            }
            
            log.info(f"[ConceptGraph] Created graph with {len(nodes)} nodes and {len(edges)} edges")
            return result
            
        except Exception as e:
            log.error(f"[ConceptGraph] Error building concept graph: {e}")
            raise
    
    def _extract_graph_elements(self, file_data: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all potential graph elements from documents."""
        
        elements = {
            "concepts": defaultdict(lambda: {"frequency": 0, "sources": [], "contexts": []}),
            "entities": defaultdict(lambda: {"frequency": 0, "sources": [], "type": "unknown"}),
            "topics": defaultdict(lambda: {"frequency": 0, "sources": [], "descriptions": []}),
            "relationships": [],
            "co_occurrences": defaultdict(lambda: defaultdict(int))
        }
        
        for file_idx, file_info in enumerate(file_data):
            file_id = file_info.get("file_id", f"file_{file_idx}")
            
            # Extract entities
            if config.get("include_entities", True) and file_info.get("entities"):
                for entity_type, entity_list in file_info["entities"].items():
                    for entity in entity_list:
                        # Handle entity as dict or string
                        if isinstance(entity, dict):
                            entity_text = entity.get("text", str(entity))
                            entity_count = entity.get("count", 1)
                        else:
                            entity_text = str(entity)
                            entity_count = 1
                        
                        entity_key = entity_text.lower().strip()
                        elements["entities"][entity_key]["frequency"] += entity_count
                        elements["entities"][entity_key]["sources"].append(file_id)
                        elements["entities"][entity_key]["type"] = entity_type
            
            # Extract topics
            if config.get("include_topics", True) and file_info.get("topics"):
                for topic in file_info["topics"]:
                    topic_key = topic.lower().strip()
                    elements["topics"][topic_key]["frequency"] += 1
                    elements["topics"][topic_key]["sources"].append(file_id)
                    
                    # Add description if available
                    if file_info.get("summary"):
                        elements["topics"][topic_key]["descriptions"].append(file_info["summary"][:100])
            
            # Extract concepts from key points
            if config.get("include_concepts", True) and file_info.get("key_points"):
                concepts = self._extract_concepts_from_key_points(file_info["key_points"])
                for concept in concepts:
                    concept_key = concept.lower().strip()
                    elements["concepts"][concept_key]["frequency"] += 1
                    elements["concepts"][concept_key]["sources"].append(file_id)
            
            # Extract relationships from evidence or analysis
            if file_info.get("evidence_items"):
                relationships = self._extract_relationships_from_evidence(file_info["evidence_items"])
                elements["relationships"].extend(relationships)
            
            # Build co-occurrence matrix
            all_terms = []
            if file_info.get("topics"):
                all_terms.extend([t.lower() for t in file_info["topics"]])
            if file_info.get("entities"):
                for entity_list in file_info["entities"].values():
                    for entity in entity_list:
                        # Handle entity as dict or string
                        if isinstance(entity, dict):
                            entity_text = entity.get("text", str(entity))
                        else:
                            entity_text = str(entity)
                        all_terms.append(entity_text.lower())
            
            # Record co-occurrences
            for i, term1 in enumerate(all_terms):
                for term2 in all_terms[i+1:]:
                    elements["co_occurrences"][term1][term2] += 1
                    elements["co_occurrences"][term2][term1] += 1
        
        return elements
    
    def _build_graph_nodes(self, elements: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build nodes for the concept graph."""
        nodes = []
        node_id = 0
        
        # Add entity nodes
        for entity, data in elements["entities"].items():
            if data["frequency"] >= 1:  # Filter low-frequency entities
                nodes.append({
                    "id": node_id,
                    "label": entity.title(),
                    "type": "entity",
                    "entity_type": data["type"],
                    "frequency": data["frequency"],
                    "sources": list(set(data["sources"])),
                    "size": min(10 + data["frequency"] * 2, 30),
                    "color": self._get_node_color("entity", data["type"]),
                    "relevance_score": self._calculate_node_relevance(data)
                })
                node_id += 1
        
        # Add topic nodes
        for topic, data in elements["topics"].items():
            if data["frequency"] >= 1:
                nodes.append({
                    "id": node_id,
                    "label": topic.title(),
                    "type": "topic",
                    "frequency": data["frequency"],
                    "sources": list(set(data["sources"])),
                    "descriptions": data["descriptions"][:3],
                    "size": min(15 + data["frequency"] * 3, 40),
                    "color": self._get_node_color("topic"),
                    "relevance_score": self._calculate_node_relevance(data)
                })
                node_id += 1
        
        # Add concept nodes
        for concept, data in elements["concepts"].items():
            if data["frequency"] >= 2:  # Higher threshold for concepts
                nodes.append({
                    "id": node_id,
                    "label": concept.title(),
                    "type": "concept",
                    "frequency": data["frequency"],
                    "sources": list(set(data["sources"])),
                    "contexts": data["contexts"][:3],
                    "size": min(12 + data["frequency"] * 2, 35),
                    "color": self._get_node_color("concept"),
                    "relevance_score": self._calculate_node_relevance(data)
                })
                node_id += 1
        
        # Sort by relevance and limit to max_nodes
        nodes.sort(key=lambda x: x["relevance_score"], reverse=True)
        max_nodes = config.get("max_nodes", 100)
        
        return nodes[:max_nodes]
    
    def _build_graph_edges(self, elements: Dict[str, Any], nodes: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build edges for the concept graph."""
        edges = []
        edge_id = 0
        
        # Create node label to ID mapping
        label_to_node = {node["label"].lower(): node["id"] for node in nodes}
        
        min_weight = config.get("min_edge_weight", 0.1)
        
        # Add co-occurrence edges
        for term1, connections in elements["co_occurrences"].items():
            if term1 in label_to_node:
                for term2, weight in connections.items():
                    if term2 in label_to_node and term1 != term2:
                        normalized_weight = min(weight / 10.0, 1.0)  # Normalize weight
                        
                        if normalized_weight >= min_weight:
                            edges.append({
                                "id": edge_id,
                                "source": label_to_node[term1],
                                "target": label_to_node[term2],
                                "weight": normalized_weight,
                                "type": "co_occurrence",
                                "width": max(1, normalized_weight * 5),
                                "opacity": min(0.3 + normalized_weight * 0.7, 1.0)
                            })
                            edge_id += 1
        
        # Add semantic relationship edges using AI
        semantic_edges = self._generate_semantic_edges(nodes, elements)
        edges.extend(semantic_edges)
        
        # Remove duplicate edges and self-loops
        edges = self._deduplicate_edges(edges)
        
        return edges
    
    def _generate_semantic_edges(self, nodes: List[Dict[str, Any]], elements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate semantic relationship edges using AI."""
        try:
            # Prepare node information for AI analysis
            node_info = []
            for node in nodes[:20]:  # Limit for AI processing
                node_info.append({
                    "id": node["id"],
                    "label": node["label"],
                    "type": node["type"]
                })
            
            relationships_prompt = f"""
            Analyze these concepts and identify semantic relationships between them.
            
            Concepts:
            {chr(10).join([f"- {node['label']} ({node['type']})" for node in node_info])}
            
            Identify relationships such as:
            - Hierarchical (parent-child, category-subcategory)
            - Causal (cause-effect)
            - Associative (related concepts)
            - Temporal (sequence, dependency)
            
            Return as JSON:
            {{
                "relationships": [
                    {{
                        "source_label": "concept1",
                        "target_label": "concept2", 
                        "relationship_type": "hierarchical|causal|associative|temporal",
                        "strength": 0.1-1.0,
                        "description": "brief explanation"
                    }}
                ]
            }}
            """
            
            messages = [
                {"role": "user", "content": relationships_prompt}
            ]
            response = self._make_openai_call(messages, max_tokens=1000)
            ai_relationships = self._parse_json_response(response)
            
            # Convert AI relationships to edges
            semantic_edges = []
            label_to_node = {node["label"].lower(): node["id"] for node in nodes}
            
            edge_id = len([]) # Start from existing edge count
            
            for rel in ai_relationships.get("relationships", []):
                source_label = rel.get("source_label", "").lower()
                target_label = rel.get("target_label", "").lower()
                
                if source_label in label_to_node and target_label in label_to_node:
                    semantic_edges.append({
                        "id": f"semantic_{edge_id}",
                        "source": label_to_node[source_label],
                        "target": label_to_node[target_label],
                        "weight": rel.get("strength", 0.5),
                        "type": rel.get("relationship_type", "associative"),
                        "description": rel.get("description", ""),
                        "width": max(2, rel.get("strength", 0.5) * 4),
                        "opacity": 0.8,
                        "style": "dashed" if rel.get("relationship_type") == "associative" else "solid"
                    })
                    edge_id += 1
            
            return semantic_edges
            
        except Exception as e:
            log.warning(f"[ConceptGraph] AI semantic edge generation failed: {e}")
            return []
    
    def _analyze_graph_structure(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the structure of the concept graph."""
        
        if not nodes:
            return {"error": "No nodes in graph"}
        
        # Build adjacency list
        adjacency = defaultdict(list)
        for edge in edges:
            adjacency[edge["source"]].append(edge["target"])
            adjacency[edge["target"]].append(edge["source"])
        
        # Calculate graph metrics
        analysis = {
            "basic_metrics": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "average_degree": len(edges) * 2 / len(nodes) if nodes else 0,
                "density": len(edges) / (len(nodes) * (len(nodes) - 1) / 2) if len(nodes) > 1 else 0
            },
            "centrality_metrics": self._calculate_centrality_metrics(nodes, edges, adjacency),
            "clustering_metrics": self._calculate_clustering_metrics(nodes, adjacency),
            "connectivity_metrics": self._analyze_connectivity(nodes, adjacency)
        }
        
        return analysis
    
    def _build_concept_hierarchies(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build hierarchical structures from the concept graph."""
        
        hierarchies = {
            "entity_hierarchy": self._build_entity_hierarchy(nodes),
            "topic_hierarchy": self._build_topic_hierarchy(nodes, edges),
            "concept_clusters": self._identify_concept_clusters(nodes, edges)
        }
        
        return hierarchies
    
    def _create_interactive_features(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create interactive features for the concept graph."""
        
        return {
            "filters": {
                "by_type": list(set(node["type"] for node in nodes)),
                "by_frequency": {
                    "min": min(node["frequency"] for node in nodes) if nodes else 0,
                    "max": max(node["frequency"] for node in nodes) if nodes else 0
                },
                "by_source": list(set(source for node in nodes for source in node.get("sources", [])))
            },
            "search": {
                "searchable_fields": ["label", "type", "sources"],
                "autocomplete_suggestions": [node["label"] for node in nodes]
            },
            "layout_options": ["force_directed", "hierarchical", "circular", "grid"],
            "export_formats": ["png", "svg", "json", "graphml"],
            "drill_down": {
                "node_details": True,
                "source_documents": True,
                "related_concepts": True
            }
        }
    
    def _generate_graph_insights(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights about the concept graph."""
        
        # Find most central concepts
        centrality = analysis.get("centrality_metrics", {})
        high_centrality_nodes = []
        
        if centrality.get("degree_centrality"):
            sorted_centrality = sorted(centrality["degree_centrality"].items(), key=lambda x: x[1], reverse=True)
            high_centrality_nodes = [
                {"node_id": node_id, "label": self._get_node_label(node_id, nodes), "centrality": score}
                for node_id, score in sorted_centrality[:5]
            ]
        
        # Identify concept themes
        themes = self._identify_themes(nodes, edges)
        
        # Generate recommendations
        recommendations = self._generate_graph_recommendations(nodes, edges, analysis)
        
        insights = {
            "key_concepts": high_centrality_nodes,
            "dominant_themes": themes,
            "graph_quality": {
                "connectivity": analysis.get("connectivity_metrics", {}).get("is_connected", False),
                "density_assessment": "sparse" if analysis.get("basic_metrics", {}).get("density", 0) < 0.1 else "dense",
                "cluster_count": len(analysis.get("clustering_metrics", {}).get("clusters", []))
            },
            "recommendations": recommendations,
            "knowledge_gaps": self._identify_knowledge_gaps(nodes, edges)
        }
        
        return insights
    
    # Helper methods
    def _extract_concepts_from_key_points(self, key_points: List[Any]) -> List[str]:
        """Extract concepts from key points."""
        concepts = []
        
        for point in key_points:
            if isinstance(point, dict) and "text" in point:
                text = point["text"]
            else:
                text = str(point)
            
            # Simple concept extraction using noun phrases
            # This could be enhanced with NLP
            words = text.split()
            for i, word in enumerate(words):
                if len(word) > 4 and word.lower() not in ['the', 'and', 'or', 'but', 'this', 'that']:
                    # Look for multi-word concepts
                    if i < len(words) - 1:
                        two_word = f"{word} {words[i+1]}"
                        if len(two_word) > 8:
                            concepts.append(two_word)
                    concepts.append(word)
        
        return list(set(concepts))[:10]  # Limit and deduplicate
    
    def _extract_relationships_from_evidence(self, evidence_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract relationships from evidence items."""
        relationships = []
        
        # This would extract relationships from evidence text
        # For now, return empty list as placeholder
        
        return relationships
    
    def _get_node_color(self, node_type: str, entity_type: str = None) -> str:
        """Get color for a node based on its type."""
        color_mapping = {
            "entity": {
                "person": "#FF6B6B",
                "organization": "#4ECDC4", 
                "location": "#45B7D1",
                "product": "#96CEB4",
                "unknown": "#DDA0DD"
            },
            "topic": "#FFEAA7",
            "concept": "#98D8C8"
        }
        
        if node_type == "entity" and entity_type:
            return color_mapping["entity"].get(entity_type, color_mapping["entity"]["unknown"])
        
        return color_mapping.get(node_type, "#CCCCCC")
    
    def _calculate_node_relevance(self, data: Dict[str, Any]) -> float:
        """Calculate relevance score for a node."""
        frequency = data.get("frequency", 0)
        source_count = len(set(data.get("sources", [])))
        
        # Simple relevance based on frequency and source diversity
        return frequency * 0.7 + source_count * 0.3
    
    def _deduplicate_edges(self, edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate edges and self-loops."""
        seen = set()
        unique_edges = []
        
        for edge in edges:
            source, target = edge["source"], edge["target"]
            
            # Skip self-loops
            if source == target:
                continue
            
            # Create normalized edge key (order-independent)
            edge_key = tuple(sorted([source, target]))
            
            if edge_key not in seen:
                seen.add(edge_key)
                unique_edges.append(edge)
        
        return unique_edges
    
    def _calculate_centrality_metrics(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], adjacency: Dict[int, List[int]]) -> Dict[str, Any]:
        """Calculate centrality metrics for nodes."""
        
        degree_centrality = {}
        for node in nodes:
            node_id = node["id"]
            degree = len(adjacency.get(node_id, []))
            degree_centrality[node_id] = degree / max(len(nodes) - 1, 1)
        
        return {
            "degree_centrality": degree_centrality,
            "betweenness_centrality": {},  # Placeholder for more complex calculation
            "closeness_centrality": {}     # Placeholder for more complex calculation
        }
    
    def _calculate_clustering_metrics(self, nodes: List[Dict[str, Any]], adjacency: Dict[int, List[int]]) -> Dict[str, Any]:
        """Calculate clustering metrics."""
        
        # Simple clustering coefficient calculation
        clustering_coefficients = {}
        
        for node in nodes:
            node_id = node["id"]
            neighbors = adjacency.get(node_id, [])
            
            if len(neighbors) < 2:
                clustering_coefficients[node_id] = 0
            else:
                # Count edges between neighbors
                edges_between_neighbors = 0
                for i, neighbor1 in enumerate(neighbors):
                    for neighbor2 in neighbors[i+1:]:
                        if neighbor2 in adjacency.get(neighbor1, []):
                            edges_between_neighbors += 1
                
                possible_edges = len(neighbors) * (len(neighbors) - 1) / 2
                clustering_coefficients[node_id] = edges_between_neighbors / possible_edges
        
        avg_clustering = sum(clustering_coefficients.values()) / len(clustering_coefficients) if clustering_coefficients else 0
        
        return {
            "clustering_coefficients": clustering_coefficients,
            "average_clustering": avg_clustering,
            "clusters": []  # Placeholder for cluster detection
        }
    
    def _analyze_connectivity(self, nodes: List[Dict[str, Any]], adjacency: Dict[int, List[int]]) -> Dict[str, Any]:
        """Analyze graph connectivity."""
        
        if not nodes:
            return {"is_connected": False, "components": 0}
        
        # Simple connectivity check using DFS
        visited = set()
        components = 0
        
        for node in nodes:
            node_id = node["id"]
            if node_id not in visited:
                # Start DFS from this node
                stack = [node_id]
                while stack:
                    current = stack.pop()
                    if current not in visited:
                        visited.add(current)
                        stack.extend(adjacency.get(current, []))
                components += 1
        
        return {
            "is_connected": components == 1,
            "components": components,
            "largest_component_size": len(visited) if components > 0 else 0
        }
    
    def _build_entity_hierarchy(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build hierarchy for entity nodes."""
        entities_by_type = defaultdict(list)
        
        for node in nodes:
            if node["type"] == "entity":
                entity_type = node.get("entity_type", "unknown")
                entities_by_type[entity_type].append(node)
        
        return dict(entities_by_type)
    
    def _build_topic_hierarchy(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build hierarchy for topic nodes."""
        topic_nodes = [node for node in nodes if node["type"] == "topic"]
        
        # Simple grouping by frequency
        high_level = [node for node in topic_nodes if node["frequency"] > 3]
        mid_level = [node for node in topic_nodes if 1 < node["frequency"] <= 3]
        low_level = [node for node in topic_nodes if node["frequency"] <= 1]
        
        return {
            "high_level_topics": high_level,
            "mid_level_topics": mid_level,
            "specific_topics": low_level
        }
    
    def _identify_concept_clusters(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify clusters of related concepts."""
        # Placeholder for more sophisticated clustering
        return []
    
    def _get_node_label(self, node_id: int, nodes: List[Dict[str, Any]]) -> str:
        """Get label for a node by its ID."""
        for node in nodes:
            if node["id"] == node_id:
                return node["label"]
        return f"Node {node_id}"
    
    def _identify_themes(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Identify dominant themes in the concept graph."""
        
        # Group nodes by type and frequency
        themes = []
        
        topic_nodes = [node for node in nodes if node["type"] == "topic"]
        if topic_nodes:
            top_topics = sorted(topic_nodes, key=lambda x: x["frequency"], reverse=True)[:3]
            for topic in top_topics:
                themes.append({
                    "theme": topic["label"],
                    "type": "topic",
                    "strength": topic["frequency"]
                })
        
        entity_nodes = [node for node in nodes if node["type"] == "entity"]
        entity_types = Counter(node.get("entity_type", "unknown") for node in entity_nodes)
        for entity_type, count in entity_types.most_common(2):
            themes.append({
                "theme": f"{entity_type.title()} Focus",
                "type": "entity_theme", 
                "strength": count
            })
        
        return themes
    
    def _generate_graph_recommendations(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving the concept graph."""
        recommendations = []
        
        # Check graph density
        density = analysis.get("basic_metrics", {}).get("density", 0)
        if density < 0.05:
            recommendations.append("Graph appears sparse - consider adding more relationships between concepts")
        elif density > 0.5:
            recommendations.append("Graph is very dense - consider filtering less important connections")
        
        # Check connectivity
        if not analysis.get("connectivity_metrics", {}).get("is_connected", True):
            recommendations.append("Graph has disconnected components - some concepts may be isolated")
        
        # Check node distribution
        node_types = Counter(node["type"] for node in nodes)
        if len(node_types) == 1:
            recommendations.append("Consider including different types of concepts (entities, topics, concepts)")
        
        return recommendations
    
    def _identify_knowledge_gaps(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Identify potential knowledge gaps in the concept graph."""
        gaps = []
        
        # Find isolated nodes
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge["source"])
            connected_nodes.add(edge["target"])
        
        isolated_nodes = [node for node in nodes if node["id"] not in connected_nodes]
        
        if isolated_nodes:
            gaps.append({
                "gap_type": "isolated_concepts",
                "description": f"{len(isolated_nodes)} concepts have no connections",
                "suggestion": "Review these concepts for potential relationships"
            })
        
        # Check for missing entity types
        entity_nodes = [node for node in nodes if node["type"] == "entity"]
        entity_types = set(node.get("entity_type", "unknown") for node in entity_nodes)
        expected_types = {"person", "organization", "location", "product"}
        missing_types = expected_types - entity_types
        
        if missing_types:
            gaps.append({
                "gap_type": "missing_entity_types",
                "description": f"Missing entity types: {', '.join(missing_types)}",
                "suggestion": "Consider adding entities of these types if relevant"
            })
        
        return gaps
