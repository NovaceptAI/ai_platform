# app/services/stages/organize/cluster_builder_service.py
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import math
from datetime import datetime
from app.services.ai_service_base import AIServiceBase

log = logging.getLogger(__name__)

class ClusterBuilderService(AIServiceBase):
    """
    Service for building document clusters using content similarity and thematic grouping.
    Creates intelligent document clusters based on semantic similarity and content analysis.
    """
    
    def __init__(self):
        super().__init__()
        self.service_name = "cluster_builder"
        
    def get_service_info(self) -> Dict[str, Any]:
        """
        Return information about the cluster builder service.
        
        Returns:
            Dictionary with service information
        """
        return {
            "service_name": self.service_name,
            "description": "Service for building document clusters using content similarity and thematic grouping",
            "capabilities": [
                "semantic_clustering",
                "content_similarity_analysis", 
                "thematic_grouping",
                "cluster_optimization"
            ],
            "supported_methods": ["semantic", "topic_based", "hybrid"],
            "version": "1.0.0"
        }
        
    def build_document_clusters(self, file_data: List[Dict[str, Any]], cluster_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build intelligent document clusters based on content similarity.
        
        Args:
            file_data: List of file analysis data with summaries, topics, etc.
            cluster_config: Optional configuration for clustering parameters
            
        Returns:
            Dict containing clusters and metadata
        """
        try:
            log.info(f"[Clustering] Building clusters for {len(file_data)} files")
            
            # Default configuration
            config = cluster_config or {
                "max_clusters": min(7, len(file_data)),
                "min_cluster_size": 1,
                "similarity_threshold": 0.3,
                "clustering_method": "semantic"
            }
            
            # 1. Calculate similarity matrix
            similarity_matrix = self._calculate_similarity_matrix(file_data)
            
            # 2. Apply clustering algorithm
            clusters = self._apply_clustering_algorithm(file_data, similarity_matrix, config)
            
            # 3. Enhance clusters with metadata
            enhanced_clusters = self._enhance_clusters(clusters, file_data, similarity_matrix)
            
            # 4. Generate cluster insights
            cluster_insights = self._generate_cluster_insights(enhanced_clusters, file_data)
            
            # 5. Create cluster visualization data
            visualization_data = self._create_visualization_data(enhanced_clusters, similarity_matrix)
            
            result = {
                "clusters": enhanced_clusters,
                "insights": cluster_insights,
                "visualization": visualization_data,
                "statistics": self._generate_cluster_statistics(enhanced_clusters, file_data),
                "configuration": config,
                "created_at": datetime.utcnow().isoformat()
            }
            
            log.info(f"[Clustering] Created {len(enhanced_clusters)} clusters")
            return result
            
        except Exception as e:
            log.error(f"[Clustering] Error building clusters: {e}")
            raise
    
    def _calculate_similarity_matrix(self, file_data: List[Dict[str, Any]]) -> List[List[float]]:
        """Calculate pairwise similarity between all documents."""
        n = len(file_data)
        similarity_matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        
        for i in range(n):
            for j in range(i, n):
                if i == j:
                    similarity_matrix[i][j] = 1.0
                else:
                    similarity = self._calculate_document_similarity(file_data[i], file_data[j])
                    similarity_matrix[i][j] = similarity
                    similarity_matrix[j][i] = similarity  # Symmetric matrix
        
        return similarity_matrix
    
    def _calculate_document_similarity(self, doc1: Dict[str, Any], doc2: Dict[str, Any]) -> float:
        """Calculate similarity between two documents."""

        # 1. Topic similarity
        topic_sim = self._calculate_topic_similarity(
            doc1.get("topics", []),
            doc2.get("topics", [])
        )

        # 2. Entity similarity
        entity_sim = self._calculate_entity_similarity(
            doc1.get("entities", {}),
            doc2.get("entities", {})
        )

        # 3. Content similarity (prefer full content if available, else use summary)
        content1 = doc1.get("content", "") or doc1.get("summary", "")
        content2 = doc2.get("content", "") or doc2.get("summary", "")
        content_sim = self._calculate_content_similarity(content1, content2)

        # 4. Keyword similarity
        keyword_sim = self._calculate_keyword_similarity(
            doc1.get("key_points", []),
            doc2.get("key_points", [])
        )

        # Weighted combination - favor content and topic similarity
        weights = {
            "topic": 0.35,
            "entity": 0.15,
            "content": 0.40,
            "keyword": 0.10
        }

        overall_similarity = (
            weights["topic"] * topic_sim +
            weights["entity"] * entity_sim +
            weights["content"] * content_sim +
            weights["keyword"] * keyword_sim
        )

        return min(overall_similarity, 1.0)
    
    def _calculate_topic_similarity(self, topics1: List, topics2: List) -> float:
        """Calculate similarity based on shared topics."""
        if not topics1 or not topics2:
            return 0.0

        # Extract topic strings from potentially mixed list of strings and dicts
        def extract_topic_text(topic):
            if isinstance(topic, str):
                return topic.lower()
            elif isinstance(topic, dict):
                return (topic.get('label') or topic.get('topic') or topic.get('name') or str(topic)).lower()
            else:
                return str(topic).lower()

        set1 = set(extract_topic_text(topic) for topic in topics1)
        set2 = set(extract_topic_text(topic) for topic in topics2)

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0
    
    def _calculate_entity_similarity(self, entities1: Dict[str, List[str]], entities2: Dict[str, List[str]]) -> float:
        """Calculate similarity based on shared entities."""
        if not entities1 or not entities2:
            return 0.0

        # Helper function to extract entity text from string or dict
        def extract_entity_text(entity):
            if isinstance(entity, str):
                return entity.lower()
            elif isinstance(entity, dict):
                return (entity.get('text') or entity.get('name') or entity.get('value') or str(entity)).lower()
            else:
                return str(entity).lower()

        # Flatten entity lists
        all_entities1 = set()
        all_entities2 = set()

        for entity_list in entities1.values():
            if isinstance(entity_list, list):
                for entity in entity_list:
                    all_entities1.add(extract_entity_text(entity))

        for entity_list in entities2.values():
            if isinstance(entity_list, list):
                for entity in entity_list:
                    all_entities2.add(extract_entity_text(entity))

        if not all_entities1 or not all_entities2:
            return 0.0

        intersection = len(all_entities1.intersection(all_entities2))
        union = len(all_entities1.union(all_entities2))

        return intersection / union if union > 0 else 0.0
    
    def _calculate_content_similarity(self, summary1: str, summary2: str) -> float:
        """Calculate similarity based on content using simple word overlap."""
        if not summary1 or not summary2:
            return 0.0
        
        # Simple word-based similarity (can be enhanced with embeddings)
        words1 = set(word.lower().strip('.,!?;:') for word in summary1.split() if len(word) > 3)
        words2 = set(word.lower().strip('.,!?;:') for word in summary2.split() if len(word) > 3)
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_keyword_similarity(self, keywords1: List[Any], keywords2: List[Any]) -> float:
        """Calculate similarity based on key points/keywords."""
        if not keywords1 or not keywords2:
            return 0.0
        
        # Extract text from key points
        text1 = " ".join([
            kp.get("text", "") if isinstance(kp, dict) else str(kp) 
            for kp in keywords1
        ])
        text2 = " ".join([
            kp.get("text", "") if isinstance(kp, dict) else str(kp) 
            for kp in keywords2
        ])
        
        return self._calculate_content_similarity(text1, text2)
    
    def _apply_clustering_algorithm(self, file_data: List[Dict[str, Any]], similarity_matrix: List[List[float]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply clustering algorithm to group similar documents."""
        
        method = config.get("clustering_method", "semantic")
        max_clusters = config.get("max_clusters", 5)
        similarity_threshold = config.get("similarity_threshold", 0.3)
        
        if method == "hierarchical":
            return self._hierarchical_clustering(file_data, similarity_matrix, max_clusters)
        elif method == "threshold":
            return self._threshold_clustering(file_data, similarity_matrix, similarity_threshold)
        else:
            return self._semantic_clustering(file_data, similarity_matrix, max_clusters)
    
    def _semantic_clustering(self, file_data: List[Dict[str, Any]], similarity_matrix: List[List[float]], max_clusters: int) -> List[Dict[str, Any]]:
        """Semantic clustering based on content similarity."""
        n = len(file_data)
        clusters = []
        assigned = [False] * n

        # Adjust max_clusters to not exceed number of items
        max_clusters = min(max_clusters, n)

        # Lower threshold for semantic chunks - they share more content naturally
        similarity_threshold = 0.15  # Lower than 0.3 to group more aggressively

        for i in range(n):
            if assigned[i]:
                continue

            # Stop if we've reached max clusters (save room for unassigned items)
            if len(clusters) >= max_clusters:
                break

            # Start new cluster
            cluster = {
                "cluster_id": f"cluster_{len(clusters)}",
                "files": [i],
                "centroid_file_idx": i,
                "cluster_type": "semantic"
            }
            assigned[i] = True

            # Find similar documents - use lower threshold for better grouping
            for j in range(i + 1, n):
                if not assigned[j] and similarity_matrix[i][j] > similarity_threshold:
                    cluster["files"].append(j)
                    assigned[j] = True

            clusters.append(cluster)

        # Assign ALL remaining documents to closest existing clusters (no new clusters)
        for i in range(n):
            if not assigned[i]:
                best_cluster = self._find_best_cluster_for_document(i, clusters, similarity_matrix)
                if best_cluster is not None:
                    best_cluster["files"].append(i)
                    assigned[i] = True
                else:
                    # Force assign to most similar cluster even if similarity is low
                    if clusters:
                        # Find cluster with highest average similarity
                        best_similarity = -1
                        best_cluster_idx = 0
                        for idx, cluster in enumerate(clusters):
                            cluster_similarities = [similarity_matrix[i][file_idx] for file_idx in cluster["files"]]
                            avg_sim = sum(cluster_similarities) / len(cluster_similarities)
                            if avg_sim > best_similarity:
                                best_similarity = avg_sim
                                best_cluster_idx = idx
                        clusters[best_cluster_idx]["files"].append(i)
                        assigned[i] = True

        return clusters
    
    def _find_best_cluster_for_document(self, doc_idx: int, clusters: List[Dict[str, Any]], similarity_matrix: List[List[float]]) -> Optional[Dict[str, Any]]:
        """Find the best cluster for a document."""
        best_cluster = None
        best_similarity = 0.0
        
        for cluster in clusters:
            # Calculate average similarity to cluster members
            cluster_similarities = [similarity_matrix[doc_idx][file_idx] for file_idx in cluster["files"]]
            avg_similarity = sum(cluster_similarities) / len(cluster_similarities)
            
            if avg_similarity > best_similarity:
                best_similarity = avg_similarity
                best_cluster = cluster
        
        return best_cluster if best_similarity > 0.2 else None
    
    def _enhance_clusters(self, clusters: List[Dict[str, Any]], file_data: List[Dict[str, Any]], similarity_matrix: List[List[float]]) -> List[Dict[str, Any]]:
        """Enhance clusters with metadata and insights."""
        enhanced_clusters = []

        for cluster in clusters:
            enhanced = cluster.copy()
            file_indices = cluster["files"]

            # Add file details - handle both semantic chunks and regular documents
            file_details = []
            for idx in file_indices:
                item = file_data[idx]
                detail = {
                    "file_id": item.get("file_id", ""),
                    "file_name": item.get("file_name", f"Document {idx + 1}"),
                    "summary": (item.get("summary", "")[:200] + "...") if item.get("summary") and len(item.get("summary", "")) > 200 else item.get("summary", ""),
                    "similarity_to_centroid": similarity_matrix[idx][cluster["centroid_file_idx"]] if "centroid_file_idx" in cluster else 0.0
                }

                # Include pages for semantic chunks
                if "pages" in item:
                    detail["pages"] = item["pages"]
                    detail["chunk_id"] = item.get("chunk_id", "")
                elif "page_number" in item:
                    detail["page_number"] = item["page_number"]

                file_details.append(detail)

            enhanced["file_details"] = file_details
            
            # Generate cluster characteristics
            enhanced["characteristics"] = self._analyze_cluster_characteristics(file_indices, file_data)
            
            # Calculate cluster metrics
            enhanced["metrics"] = self._calculate_cluster_metrics(file_indices, similarity_matrix)
            
            # Generate cluster name and description
            cluster_summary = self._generate_cluster_summary(file_indices, file_data)
            enhanced["name"] = cluster_summary["name"]
            enhanced["description"] = cluster_summary["description"]
            
            # Add cluster quality score
            enhanced["quality_score"] = self._calculate_cluster_quality(file_indices, similarity_matrix)
            
            enhanced_clusters.append(enhanced)
        
        return enhanced_clusters
    
    def _analyze_cluster_characteristics(self, file_indices: List[int], file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the characteristics of a cluster."""
        # Collect all topics and entities from cluster files
        all_topics = []
        all_entities = defaultdict(list)

        for idx in file_indices:
            file_info = file_data[idx]

            if file_info.get("topics"):
                # Handle both string topics and dict topics
                for topic in file_info["topics"]:
                    if isinstance(topic, str):
                        all_topics.append(topic)
                    elif isinstance(topic, dict):
                        topic_text = topic.get('label') or topic.get('topic') or topic.get('name') or str(topic)
                        all_topics.append(topic_text)
                    else:
                        all_topics.append(str(topic))

            if file_info.get("entities"):
                for entity_type, entities in file_info["entities"].items():
                    # Handle both list of strings and list of dicts
                    if isinstance(entities, list):
                        for entity in entities:
                            if isinstance(entity, str):
                                all_entities[entity_type].append(entity)
                            elif isinstance(entity, dict):
                                # If entity is a dict, try to extract text/name field
                                entity_text = entity.get('text') or entity.get('name') or entity.get('value') or str(entity)
                                all_entities[entity_type].append(entity_text)
                            else:
                                all_entities[entity_type].append(str(entity))

        # Find common characteristics
        topic_counts = defaultdict(int)
        for topic in all_topics:
            topic_counts[topic] += 1

        common_topics = [
            topic for topic, count in topic_counts.items()
            if count >= max(1, len(file_indices) // 2)
        ]

        # Create unique entity lists (now all are strings, so set() will work)
        dominant_entities = {}
        for entity_type, entities in all_entities.items():
            try:
                # Remove duplicates and take top 3
                unique_entities = list(set(entities))[:3]
                dominant_entities[entity_type] = unique_entities
            except TypeError:
                # If still unhashable, just take first 3 unique by manual dedup
                seen = []
                for e in entities:
                    if e not in seen:
                        seen.append(e)
                        if len(seen) >= 3:
                            break
                dominant_entities[entity_type] = seen

        return {
            "common_topics": common_topics[:5],
            "dominant_entities": dominant_entities,
            "cluster_size": len(file_indices),
            "content_diversity": self._calculate_cluster_diversity(file_indices, file_data)
        }
    
    def _calculate_cluster_metrics(self, file_indices: List[int], similarity_matrix: List[List[float]]) -> Dict[str, float]:
        """Calculate various metrics for a cluster."""
        if len(file_indices) <= 1:
            return {"cohesion": 1.0, "avg_similarity": 1.0, "diameter": 0.0}
        
        # Calculate intra-cluster similarities
        similarities = []
        for i in range(len(file_indices)):
            for j in range(i + 1, len(file_indices)):
                similarities.append(similarity_matrix[file_indices[i]][file_indices[j]])
        
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        cohesion = avg_similarity  # Simple cohesion measure
        diameter = max(similarities) - min(similarities) if similarities else 0.0
        
        return {
            "cohesion": cohesion,
            "avg_similarity": avg_similarity,
            "diameter": diameter
        }
    
    def _generate_cluster_summary(self, file_indices: List[int], file_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Generate a name and description for the cluster."""

        # Collect summaries and topics
        summaries = [file_data[idx].get("summary", "") for idx in file_indices]
        all_topics = []
        for idx in file_indices:
            topics = file_data[idx].get("topics", [])
            for topic in topics:
                if isinstance(topic, str):
                    all_topics.append(topic)
                elif isinstance(topic, dict):
                    topic_text = topic.get('label') or topic.get('topic') or topic.get('name') or str(topic)
                    all_topics.append(topic_text)
                else:
                    all_topics.append(str(topic))

        # Find most common topics
        topic_counts = defaultdict(int)
        for topic in all_topics:
            topic_counts[topic] += 1

        top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        # Check if this is content/page clustering (has pages or page_number field)
        is_content_clustering = any("pages" in file_data[idx] or "page_number" in file_data[idx] for idx in file_indices)

        # Helper to extract all page numbers from semantic chunks
        def get_all_pages():
            all_pages = []
            for idx in file_indices:
                item = file_data[idx]
                if "pages" in item:
                    all_pages.extend(item.get("pages", []))
                elif "page_number" in item:
                    all_pages.append(item.get("page_number", 0))
            return sorted(set(all_pages)) if all_pages else [1]

        if top_topics:
            # Clean up topic name for title
            main_topic = top_topics[0][0].title().replace("_", " ")
            if is_content_clustering:
                name = f"{main_topic}"
                # Include page numbers in description
                page_nums = get_all_pages()
                if len(page_nums) == 1:
                    description = f"Page {page_nums[0]}: Content related to {', '.join([topic for topic, _ in top_topics])}"
                else:
                    description = f"Pages {page_nums[0]}-{page_nums[-1]}: Content related to {', '.join([topic for topic, _ in top_topics])}"
            else:
                name = f"{main_topic} Cluster"
                description = f"Documents related to {', '.join([topic for topic, _ in top_topics])}"
        else:
            # Try to extract key terms from summaries if no topics
            all_words = []
            for summary in summaries:
                if summary:
                    words = [w.lower().strip('.,!?;:()[]"\'') for w in summary.split() if len(w) > 6 and w.isalpha()]
                    all_words.extend(words)

            word_counts = defaultdict(int)
            for word in all_words:
                word_counts[word] += 1

            top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            if top_words and is_content_clustering:
                name = f"{top_words[0][0].title()}"
                page_nums = get_all_pages()
                if len(page_nums) == 1:
                    description = f"Page {page_nums[0]}: Content about {', '.join([w for w, _ in top_words])}"
                else:
                    description = f"Pages {page_nums[0]}-{page_nums[-1]}: Content about {', '.join([w for w, _ in top_words])}"
            elif top_words:
                name = f"{top_words[0][0].title()} Cluster"
                description = f"Documents about {', '.join([w for w, _ in top_words])}"
            elif is_content_clustering:
                page_nums = get_all_pages()
                name = f"Section {file_indices[0] + 1}"
                description = f"Pages {page_nums[0]}-{page_nums[-1]}: Related content"
            else:
                name = f"Document Cluster {file_indices[0] + 1}"
                description = f"Collection of {len(file_indices)} related documents"

        return {"name": name, "description": description}
    
    def _calculate_cluster_quality(self, file_indices: List[int], similarity_matrix: List[List[float]]) -> float:
        """Calculate a quality score for the cluster (0.0 to 1.0)."""
        if len(file_indices) <= 1:
            return 1.0
        
        # Quality based on intra-cluster similarity
        similarities = []
        for i in range(len(file_indices)):
            for j in range(i + 1, len(file_indices)):
                similarities.append(similarity_matrix[file_indices[i]][file_indices[j]])
        
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        return avg_similarity
    
    def _calculate_cluster_diversity(self, file_indices: List[int], file_data: List[Dict[str, Any]]) -> float:
        """Calculate content diversity within the cluster."""
        if len(file_indices) <= 1:
            return 0.0
        
        # Simple diversity based on unique topics
        all_topics = set()
        total_topics = 0
        
        for idx in file_indices:
            topics = file_data[idx].get("topics", [])
            all_topics.update(topics)
            total_topics += len(topics)
        
        return len(all_topics) / max(total_topics, 1) if total_topics > 0 else 0.0
    
    def _generate_cluster_insights(self, clusters: List[Dict[str, Any]], file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate insights about the clustering results."""
        
        total_files = len(file_data)
        cluster_sizes = [len(cluster["files"]) for cluster in clusters]
        
        insights = {
            "clustering_summary": {
                "total_clusters": len(clusters),
                "largest_cluster_size": max(cluster_sizes) if cluster_sizes else 0,
                "smallest_cluster_size": min(cluster_sizes) if cluster_sizes else 0,
                "average_cluster_size": sum(cluster_sizes) / len(cluster_sizes) if cluster_sizes else 0,
                "singleton_clusters": len([size for size in cluster_sizes if size == 1])
            },
            "quality_assessment": {
                "overall_quality": sum(cluster.get("quality_score", 0) for cluster in clusters) / len(clusters) if clusters else 0,
                "well_formed_clusters": len([cluster for cluster in clusters if cluster.get("quality_score", 0) > 0.5]),
                "clustering_effectiveness": (total_files - len([size for size in cluster_sizes if size == 1])) / total_files if total_files > 0 else 0
            },
            "recommendations": self._generate_clustering_recommendations(clusters),
            "dominant_themes": self._extract_dominant_themes(clusters)
        }
        
        return insights
    
    def _generate_clustering_recommendations(self, clusters: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations for improving clustering."""
        recommendations = []
        
        # Check for singleton clusters
        singleton_count = len([cluster for cluster in clusters if len(cluster["files"]) == 1])
        if singleton_count > len(clusters) // 3:
            recommendations.append("Consider reducing similarity threshold to merge singleton clusters")
        
        # Check for very large clusters
        large_clusters = [cluster for cluster in clusters if len(cluster["files"]) > 10]
        if large_clusters:
            recommendations.append("Consider subdividing large clusters for better organization")
        
        # Check cluster quality
        low_quality_clusters = [cluster for cluster in clusters if cluster.get("quality_score", 0) < 0.3]
        if low_quality_clusters:
            recommendations.append("Some clusters have low coherence - consider manual review")
        
        return recommendations
    
    def _extract_dominant_themes(self, clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract the dominant themes across all clusters."""
        theme_counts = defaultdict(int)
        
        for cluster in clusters:
            common_topics = cluster.get("characteristics", {}).get("common_topics", [])
            for topic in common_topics:
                theme_counts[topic] += 1
        
        dominant_themes = [
            {"theme": theme, "cluster_count": count, "prevalence": count / len(clusters)}
            for theme, count in sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        return dominant_themes
    
    def _create_visualization_data(self, clusters: List[Dict[str, Any]], similarity_matrix: List[List[float]]) -> Dict[str, Any]:
        """Create data for cluster visualization."""
        
        # Create nodes for each document
        nodes = []
        edges = []
        
        node_id = 0
        for cluster_idx, cluster in enumerate(clusters):
            for file_idx in cluster["files"]:
                nodes.append({
                    "id": node_id,
                    "file_idx": file_idx,
                    "cluster_id": cluster_idx,
                    "cluster_name": cluster.get("name", f"Cluster {cluster_idx}"),
                    "file_name": cluster["file_details"][cluster["files"].index(file_idx)]["file_name"],
                    "x": cluster_idx * 100 + (node_id % 10) * 20,  # Simple layout
                    "y": (node_id // 10) * 50,
                    "size": 10 + len(cluster["files"]) * 2
                })
                node_id += 1
        
        # Create edges for high similarity
        for i in range(len(similarity_matrix)):
            for j in range(i + 1, len(similarity_matrix)):
                if similarity_matrix[i][j] > 0.5:  # Only show high similarity edges
                    edges.append({
                        "source": i,
                        "target": j,
                        "weight": similarity_matrix[i][j],
                        "width": similarity_matrix[i][j] * 5
                    })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "layout": "force_directed",
            "color_scheme": "cluster_based",
            "legend": [
                {"cluster_id": idx, "color": self._get_cluster_color(idx), "name": cluster.get("name", f"Cluster {idx}")}
                for idx, cluster in enumerate(clusters)
            ]
        }
    
    def _get_cluster_color(self, cluster_idx: int) -> str:
        """Get a color for a cluster."""
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8"]
        return colors[cluster_idx % len(colors)]
    
    def _generate_cluster_statistics(self, clusters: List[Dict[str, Any]], file_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive statistics about the clustering."""
        
        cluster_sizes = [len(cluster["files"]) for cluster in clusters]
        quality_scores = [cluster.get("quality_score", 0) for cluster in clusters]
        
        return {
            "total_documents": len(file_data),
            "total_clusters": len(clusters),
            "cluster_size_distribution": {
                "min": min(cluster_sizes) if cluster_sizes else 0,
                "max": max(cluster_sizes) if cluster_sizes else 0,
                "mean": sum(cluster_sizes) / len(cluster_sizes) if cluster_sizes else 0,
                "median": sorted(cluster_sizes)[len(cluster_sizes) // 2] if cluster_sizes else 0
            },
            "quality_metrics": {
                "average_quality": sum(quality_scores) / len(quality_scores) if quality_scores else 0,
                "best_cluster_quality": max(quality_scores) if quality_scores else 0,
                "worst_cluster_quality": min(quality_scores) if quality_scores else 0
            },
            "clustering_efficiency": {
                "documents_clustered": sum(cluster_sizes),
                "clustering_ratio": sum(cluster_sizes) / len(file_data) if file_data else 0,
                "singleton_ratio": len([size for size in cluster_sizes if size == 1]) / len(clusters) if clusters else 0
            }
        }
    
    # Placeholder methods for other clustering algorithms
    def _hierarchical_clustering(self, file_data: List[Dict[str, Any]], similarity_matrix: List[List[float]], max_clusters: int) -> List[Dict[str, Any]]:
        """Hierarchical clustering implementation."""
        # For now, fall back to semantic clustering
        return self._semantic_clustering(file_data, similarity_matrix, max_clusters)
    
    def _threshold_clustering(self, file_data: List[Dict[str, Any]], similarity_matrix: List[List[float]], threshold: float) -> List[Dict[str, Any]]:
        """Threshold-based clustering implementation."""
        # For now, fall back to semantic clustering
        return self._semantic_clustering(file_data, similarity_matrix, 5)
