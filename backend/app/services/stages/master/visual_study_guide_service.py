import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from app.services.ai_service_base import AIServiceBase

log = logging.getLogger(__name__)

class VisualStudyGuideService(AIServiceBase):
    """
    Service for creating visual study guides for master stage learning.
    Provides structured study materials with visual learning approaches.
    """
    
    def __init__(self):
        super().__init__()
        self.service_name = "visual_study_guide"
        
    def get_service_info(self) -> Dict[str, Any]:
        """Return information about the visual study guide service."""
        return {
            "service_name": self.service_name,
            "description": "Service for creating visual study guides and learning materials",
            "capabilities": [
                "concept_mapping",
                "visual_diagrams",
                "study_timelines",
                "interactive_guides"
            ],
            "supported_formats": ["concept_maps", "flowcharts", "timelines", "infographics"],
            "version": "1.0.0"
        }
        
    def create_visual_study_guide(self, file_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a visual study guide from file content.
        
        Args:
            file_data: Dictionary containing file content and metadata
            options: Optional configuration for visual guide creation
            
        Returns:
            Dict containing visual study guide materials
        """
        try:
            log.info(f"[VisualStudyGuide] Creating guide for file: {file_data.get('file_name', 'Unknown')}")
            
            config = options or {
                "include_concept_maps": True,
                "include_timelines": True,
                "include_diagrams": True,
                "style": "modern"
            }
            
            # Extract content for visual guide creation
            content = self._prepare_content(file_data)
            
            # Generate visual study guide components
            guide = {}
            
            # 1. Study overview and summary
            overview = self._create_study_overview(content, config)
            guide["overview"] = overview
            
            # 2. Visual learning topics
            if config.get("include_concept_maps", True):
                topics = self._create_visual_topics(content, config)
                guide["visual_topics"] = topics
            
            # 3. Study progression timeline
            if config.get("include_timelines", True):
                timeline = self._create_study_timeline(content, config)
                guide["study_timeline"] = timeline
                
            # 4. Visual diagrams and concepts
            if config.get("include_diagrams", True):
                diagrams = self._create_concept_diagrams(content, config)
                guide["concept_diagrams"] = diagrams
            
            # 5. Interactive study elements
            interactive = self._create_interactive_elements(content, config)
            guide["interactive_elements"] = interactive
            
            result = {
                "visual_study_guide": guide,
                "metadata": {
                    "style": config.get("style", "modern"),
                    "total_topics": len(guide.get("visual_topics", [])),
                    "estimated_time": self._calculate_study_time(guide),
                    "difficulty_level": self._assess_difficulty(content)
                },
                "study_plan": {
                    "recommended_sequence": [
                        "overview", 
                        "visual_topics", 
                        "concept_diagrams", 
                        "interactive_elements",
                        "study_timeline"
                    ],
                    "study_modes": ["visual", "interactive", "sequential"],
                    "best_practices": [
                        "Start with overview to get big picture",
                        "Use visual topics for main concepts",
                        "Practice with interactive elements",
                        "Follow timeline for structured learning"
                    ]
                },
                "created_at": datetime.utcnow().isoformat()
            }
            
            log.info(f"[VisualStudyGuide] Created guide with {len(guide)} sections")
            return result
            
        except Exception as e:
            log.error(f"[VisualStudyGuide] Error creating visual study guide: {e}")
            raise
    
    def _prepare_content(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and extract content for visual guide creation."""
        
        content = {
            "text": file_data.get("content", ""),
            "summary": file_data.get("summary", ""),
            "topics": file_data.get("topics", []),
            "entities": file_data.get("entities", {}),
            "key_points": file_data.get("key_points", [])
        }
        
        return content
    
    def _create_study_overview(self, content: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Create study overview with visual elements."""
        
        # Generate overview summary
        overview_text = self._generate_visual_overview(content["text"], content["summary"])
        
        overview = {
            "title": "Study Guide Overview",
            "summary": overview_text,
            "key_concepts": self._extract_key_concepts(content),
            "learning_objectives": self._create_learning_objectives(content),
            "visual_elements": {
                "mind_map_suggested": True,
                "concept_hierarchy": self._create_concept_hierarchy(content),
                "color_coding": {
                    "main_concepts": "#3B82F6",
                    "supporting_ideas": "#10B981", 
                    "examples": "#F59E0B",
                    "definitions": "#8B5CF6"
                }
            }
        }
        
        return overview
    
    def _create_visual_topics(self, content: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create visual learning topics with study methods."""
        
        visual_topics = []
        topics = content.get("topics", [])
        
        # Create visual topics from main content topics
        for i, topic in enumerate(topics[:8]):  # Limit to 8 visual topics
            if isinstance(topic, str) and len(topic) > 3:
                visual_topic = self._generate_visual_topic(topic, content["text"])
                
                visual_topics.append({
                    "name": topic,
                    "order": i + 1,
                    "study_method": visual_topic["method"],
                    "visual_approach": visual_topic["approach"],
                    "time_estimate": visual_topic["time"],
                    "visual_elements": visual_topic["elements"],
                    "practice_activities": visual_topic["activities"]
                })
        
        return visual_topics
    
    def _create_study_timeline(self, content: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a study timeline with progressive learning."""
        
        topics = content.get("topics", [])
        total_topics = min(len(topics), 8)
        
        timeline = {
            "title": "Visual Learning Timeline",
            "total_duration": f"{total_topics * 25}-{total_topics * 35} minutes",
            "phases": []
        }
        
        # Create timeline phases
        phases = [
            {
                "phase": "Preparation",
                "duration": "5-10 minutes",
                "activities": [
                    "Review study guide overview",
                    "Gather visual materials (colored pens, sticky notes)",
                    "Set up study space"
                ],
                "visual_tips": "Use color coding from overview"
            },
            {
                "phase": "Visual Exploration", 
                "duration": f"{total_topics * 15}-{total_topics * 20} minutes",
                "activities": [
                    "Work through visual topics in order",
                    "Create concept maps for each topic",
                    "Use diagrams and visual aids"
                ],
                "visual_tips": "Draw connections between concepts"
            },
            {
                "phase": "Interactive Practice",
                "duration": "10-15 minutes", 
                "activities": [
                    "Complete interactive elements",
                    "Test understanding with visual exercises",
                    "Create personal visual summaries"
                ],
                "visual_tips": "Use different colors for different concept types"
            }
        ]
        
        timeline["phases"] = phases
        return timeline
    
    def _create_concept_diagrams(self, content: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create visual concept diagrams and mappings."""
        
        diagrams = []
        key_points = content.get("key_points", [])
        
        # Create diagrams from key points
        for i, point in enumerate(key_points[:4]):  # Limit to 4 diagrams
            if isinstance(point, dict):
                text = point.get("text", "")
            else:
                text = str(point)
            
            if text and len(text) > 10:
                diagram = self._generate_concept_diagram(text, content["text"])
                
                diagrams.append({
                    "title": f"Concept Diagram {i + 1}",
                    "concept": text[:100],
                    "diagram_type": diagram["type"],
                    "elements": diagram["elements"],
                    "connections": diagram["connections"],
                    "visual_instructions": diagram["instructions"]
                })
        
        return diagrams
    
    def _create_interactive_elements(self, content: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create interactive study elements."""
        
        interactive = []
        topics = content.get("topics", [])
        
        # Create interactive elements for main topics
        for topic in topics[:5]:  # Limit to 5 interactive elements
            if isinstance(topic, str) and len(topic) > 3:
                element = self._generate_interactive_element(topic, content["text"])
                
                interactive.append({
                    "type": element["type"],
                    "title": f"Interactive: {topic}",
                    "description": element["description"],
                    "activity": element["activity"],
                    "visual_component": element["visual"],
                    "engagement_level": element["engagement"]
                })
        
        return interactive
    
    def _extract_key_concepts(self, content: Dict[str, Any]) -> List[str]:
        """Extract key concepts for visual representation."""
        
        concepts = []
        
        # Add main topics
        topics = content.get("topics", [])
        for topic in topics[:6]:
            if isinstance(topic, str) and len(topic) > 2:
                concepts.append(topic)
        
        # Add entity concepts
        entities = content.get("entities", {})
        if isinstance(entities, dict):
            for category, items in entities.items():
                if isinstance(items, list):
                    concepts.extend([str(item) for item in items[:2]])
                elif isinstance(items, str):
                    concepts.append(items)
        
        return concepts[:10]  # Limit to 10 key concepts
    
    def _create_learning_objectives(self, content: Dict[str, Any]) -> List[str]:
        """Create learning objectives for the study guide."""
        
        topics = content.get("topics", [])
        
        objectives = [
            f"Understand the main concepts related to {', '.join(str(t) for t in topics[:3])}" if topics else "Understand the main concepts in the material",
            "Create visual representations of key ideas",
            "Apply learned concepts through interactive exercises",
            "Develop connections between different topics"
        ]
        
        return objectives
    
    def _create_concept_hierarchy(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Create a concept hierarchy for visual organization."""
        
        topics = content.get("topics", [])
        
        hierarchy = {
            "main_topic": topics[0] if topics else "Main Subject",
            "subtopics": topics[1:4] if len(topics) > 1 else [],
            "supporting_concepts": topics[4:7] if len(topics) > 4 else [],
            "details": [str(kp.get("text", kp))[:50] for kp in content.get("key_points", [])[:3]]
        }
        
        return hierarchy
    
    def _generate_visual_overview(self, text: str, summary: str) -> str:
        """Generate a visual-focused overview."""
        
        try:
            prompt = f"""
            Create a visual study guide overview that emphasizes visual learning approaches.
            Focus on how students can use visual techniques to understand this material.
            Keep it under 150 words and mention specific visual strategies.
            
            Content: {text[:800]}
            Summary: {summary[:300]}
            
            Visual overview:
            """
            
            response = self._make_openai_call(prompt, max_tokens=200)
            return response.strip() or f"This study guide focuses on visual learning approaches for understanding {summary[:100]}..."
            
        except Exception as e:
            log.warning(f"[VisualStudyGuide] AI overview generation failed: {e}")
            return f"This visual study guide helps you understand the key concepts through diagrams, mind maps, and interactive visual elements."
    
    def _generate_visual_topic(self, topic: str, context: str) -> Dict[str, Any]:
        """Generate visual learning approach for a topic."""
        
        visual_approaches = [
            "mind mapping", "concept diagrams", "flowcharts", "visual timelines",
            "color-coded notes", "graphic organizers", "sketch notes", "comparison charts"
        ]
        
        return {
            "method": f"Use {visual_approaches[hash(topic) % len(visual_approaches)]} to understand {topic}",
            "approach": "visual",
            "time": f"{20 + (hash(topic) % 20)}",
            "elements": ["diagrams", "color coding", "visual connections"],
            "activities": [
                f"Create a visual map of {topic}",
                f"Draw connections to related concepts",
                f"Use colors to categorize information about {topic}"
            ]
        }
    
    def _generate_concept_diagram(self, concept: str, context: str) -> Dict[str, Any]:
        """Generate concept diagram specification."""
        
        diagram_types = ["mind_map", "flowchart", "hierarchy", "network", "timeline"]
        
        return {
            "type": diagram_types[hash(concept) % len(diagram_types)],
            "elements": [
                {"type": "central_node", "text": concept[:50], "color": "#3B82F6"},
                {"type": "branch_node", "text": "Key Aspect 1", "color": "#10B981"},
                {"type": "branch_node", "text": "Key Aspect 2", "color": "#10B981"},
                {"type": "detail_node", "text": "Supporting Detail", "color": "#F59E0B"}
            ],
            "connections": [
                {"from": "central", "to": "branch1", "type": "relates_to"},
                {"from": "central", "to": "branch2", "type": "relates_to"}
            ],
            "instructions": f"Place '{concept[:30]}' at center, connect related concepts with lines, use colors to show relationships"
        }
    
    def _generate_interactive_element(self, topic: str, context: str) -> Dict[str, Any]:
        """Generate interactive study element."""
        
        element_types = ["drag_and_drop", "matching", "sorting", "building", "drawing"]
        
        return {
            "type": element_types[hash(topic) % len(element_types)],
            "description": f"Interactive activity to explore {topic}",
            "activity": f"Organize and connect concepts related to {topic}",
            "visual": "Use visual elements to make connections clear",
            "engagement": "high"
        }
    
    def _calculate_study_time(self, guide: Dict[str, Any]) -> str:
        """Calculate estimated study time."""
        
        base_time = 15  # Base overview time
        topics_time = len(guide.get("visual_topics", [])) * 20
        diagrams_time = len(guide.get("concept_diagrams", [])) * 10
        interactive_time = len(guide.get("interactive_elements", [])) * 15
        
        total_min = base_time + topics_time + diagrams_time + interactive_time
        
        return f"{total_min}-{total_min + 20} minutes"
    
    def _assess_difficulty(self, content: Dict[str, Any]) -> str:
        """Assess difficulty level based on content complexity."""
        
        topics_count = len(content.get("topics", []))
        text_length = len(content.get("text", ""))
        
        if topics_count > 6 or text_length > 5000:
            return "advanced"
        elif topics_count > 3 or text_length > 2000:
            return "intermediate"
        else:
            return "beginner"
