"""
Learn by Drawing Service

Hybrid AI service using Azure Computer Vision + GPT-4 Vision for educational drawing analysis.

Stage 1: Basic drawing recognition with educational feedback
Stage 2: Multi-step guidance, badges, voice feedback
"""

import logging
import os
import json
import base64
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.services.ai_service_base import AIServiceBase

logger = logging.getLogger(__name__)


class LearnByDrawingService(AIServiceBase):
    """Service for analyzing student drawings with AI."""

    def __init__(self):
        super().__init__()
        self.service_name = "LearnByDrawing"
        self.model_name = "gpt-4o"

        # Azure Computer Vision credentials
        self.azure_cv_endpoint = os.getenv("AZURE_VISION_ENDPOINT")
        self.azure_cv_key = os.getenv("AZURE_VISION_KEY")

    # ==================== Service Info ====================

    def get_service_info(self) -> Dict[str, Any]:
        """Return service metadata."""
        return {
            'service_name': 'LearnByDrawing',
            'description': 'AI-powered educational drawing analysis',
            'version': '1.0',
            'stage': 1,
            'capabilities': [
                'drawing_recognition',
                'topic_identification',
                'educational_feedback',
                'concept_validation',
                'progress_tracking'
            ],
            'topics': self.get_available_topics(),
            'age_groups': ['5-7', '8-10', '11-13', '14+']
        }

    def get_available_topics(self) -> List[Dict[str, Any]]:
        """Get available learning topics."""
        return [
            {
                'id': 'water_cycle',
                'name': 'Water Cycle',
                'description': 'Learn about evaporation, condensation, and precipitation',
                'key_concepts': ['evaporation', 'condensation', 'precipitation', 'collection'],
                'expected_objects': ['sun', 'cloud', 'rain', 'water', 'ocean', 'lake', 'river', 'arrow'],
                'category': 'science',
                'difficulty': 'easy',
                'icon': '💧'
            },
            {
                'id': 'plant_structure',
                'name': 'Plant Structure',
                'description': 'Parts of a plant and their functions',
                'key_concepts': ['roots', 'stem', 'leaves', 'flower', 'photosynthesis'],
                'expected_objects': ['roots', 'stem', 'leaves', 'flower', 'soil', 'sun'],
                'category': 'biology',
                'difficulty': 'easy',
                'icon': '🌱'
            },
            {
                'id': 'solar_system',
                'name': 'Solar System',
                'description': 'Planets orbiting the sun',
                'key_concepts': ['sun', 'planets', 'orbits', 'asteroid belt', 'scale'],
                'expected_objects': ['sun', 'mercury', 'venus', 'earth', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune'],
                'category': 'astronomy',
                'difficulty': 'medium',
                'icon': '🪐'
            },
            {
                'id': 'basic_shapes',
                'name': 'Basic Shapes',
                'description': 'Geometric shapes and their properties',
                'key_concepts': ['circle', 'square', 'triangle', 'rectangle', 'sides', 'angles'],
                'expected_objects': ['circle', 'square', 'triangle', 'rectangle', 'pentagon', 'hexagon'],
                'category': 'math',
                'difficulty': 'easy',
                'icon': '🔺'
            },
            {
                'id': 'food_chain',
                'name': 'Food Chain',
                'description': 'Energy transfer in ecosystems',
                'key_concepts': ['producer', 'consumer', 'predator', 'prey', 'decomposer', 'energy flow'],
                'expected_objects': ['sun', 'plant', 'herbivore', 'carnivore', 'arrow', 'grass', 'rabbit', 'fox'],
                'category': 'biology',
                'difficulty': 'medium',
                'icon': '🦊'
            },
            {
                'id': 'cell_structure',
                'name': 'Cell Structure',
                'description': 'Parts of a cell and their functions',
                'key_concepts': ['nucleus', 'membrane', 'cytoplasm', 'mitochondria', 'cell wall'],
                'expected_objects': ['nucleus', 'membrane', 'cytoplasm', 'mitochondria', 'cell wall', 'vacuole'],
                'category': 'biology',
                'difficulty': 'hard',
                'icon': '🧬'
            },
            {
                'id': 'human_body',
                'name': 'Human Body Systems',
                'description': 'Major organs and body systems',
                'key_concepts': ['heart', 'lungs', 'brain', 'stomach', 'skeleton', 'muscles'],
                'expected_objects': ['heart', 'lungs', 'brain', 'stomach', 'bones', 'muscles'],
                'category': 'biology',
                'difficulty': 'medium',
                'icon': '🫁'
            },
            {
                'id': 'landforms',
                'name': 'Landforms',
                'description': 'Geographic features of Earth',
                'key_concepts': ['mountain', 'valley', 'river', 'ocean', 'plain', 'plateau'],
                'expected_objects': ['mountain', 'valley', 'river', 'ocean', 'plain', 'lake', 'hill'],
                'category': 'geography',
                'difficulty': 'easy',
                'icon': '��️'
            },
            {
                'id': 'fractions',
                'name': 'Fractions',
                'description': 'Parts of a whole',
                'key_concepts': ['numerator', 'denominator', 'half', 'quarter', 'third', 'equivalent'],
                'expected_objects': ['circle', 'rectangle', 'pizza', 'pie', 'divisions', 'numbers'],
                'category': 'math',
                'difficulty': 'medium',
                'icon': '🍕'
            },
            {
                'id': 'graphs',
                'name': 'Bar Graphs',
                'description': 'Representing data visually',
                'key_concepts': ['x-axis', 'y-axis', 'bars', 'labels', 'scale', 'data'],
                'expected_objects': ['axis', 'bars', 'labels', 'title', 'numbers', 'grid'],
                'category': 'math',
                'difficulty': 'medium',
                'icon': '📊'
            }
        ]

    # ==================== Azure Computer Vision ====================

    def analyze_with_azure_cv(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Quick object detection with Azure Computer Vision.

        Returns tags, description, and confidence scores.
        """
        if not self.azure_cv_endpoint or not self.azure_cv_key:
            logger.warning("[LearnByDrawing] Azure CV credentials not configured")
            return {'tags': [], 'description': '', 'confidence': 0.0}

        analyze_url = f"{self.azure_cv_endpoint}/vision/v3.2/analyze"

        headers = {
            'Ocp-Apim-Subscription-Key': self.azure_cv_key,
            'Content-Type': 'application/octet-stream'
        }

        params = {
            'visualFeatures': 'Categories,Tags,Description,Objects,Color',
            'language': 'en'
        }

        try:
            response = requests.post(
                analyze_url,
                headers=headers,
                params=params,
                data=image_bytes,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # Extract relevant data
            tags = [
                {'name': tag['name'], 'confidence': tag['confidence']}
                for tag in result.get('tags', [])
            ]

            description = result.get('description', {}).get('captions', [{}])[0].get('text', '')
            confidence = result.get('description', {}).get('captions', [{}])[0].get('confidence', 0.0)

            objects_detected = [
                {'object': obj['object'], 'confidence': obj['confidence']}
                for obj in result.get('objects', [])
            ]

            logger.info(f"[LearnByDrawing] Azure CV detected {len(tags)} tags, description: {description}")

            return {
                'tags': tags,
                'description': description,
                'confidence': confidence,
                'objects': objects_detected,
                'colors': result.get('color', {})
            }

        except Exception as e:
            logger.error(f"[LearnByDrawing] Azure CV error: {str(e)}")
            return {'tags': [], 'description': '', 'confidence': 0.0, 'objects': []}

    # ==================== GPT-4 Vision Analysis ====================

    def analyze_with_gpt4_vision(
        self,
        image_bytes: bytes,
        topic: str,
        age_group: str,
        azure_cv_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detailed educational analysis with GPT-4 Vision.

        Args:
            image_bytes: PNG image bytes
            topic: Selected topic (water_cycle, plant_structure, etc.)
            age_group: Student age group (5-7, 8-10, 11-13, 14+)
            azure_cv_data: Pre-analysis from Azure CV

        Returns:
            Detailed analysis with educational feedback
        """

        # Get topic details
        topic_data = next((t for t in self.get_available_topics() if t['id'] == topic), None)

        if not topic_data:
            topic_data = {'name': topic, 'key_concepts': [], 'expected_objects': []}

        # Encode image to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        # Create age-appropriate prompt
        age_instructions = {
            '5-7': 'simple language for young children (ages 5-7)',
            '8-10': 'clear language for elementary students (ages 8-10)',
            '11-13': 'detailed explanations for middle school students (ages 11-13)',
            '14+': 'comprehensive explanations for high school students (ages 14+)'
        }

        age_instruction = age_instructions.get(age_group, 'age-appropriate language')

        prompt = f"""Analyze this drawing made by a student learning about "{topic_data['name']}".

Topic Details:
- Key concepts to look for: {', '.join(topic_data['key_concepts'][:8])}
- Expected elements: {', '.join(topic_data['expected_objects'][:10])}

Azure Computer Vision Pre-analysis:
- Description: {azure_cv_data.get('description', 'N/A')}
- Detected tags: {', '.join([t['name'] for t in azure_cv_data.get('tags', [])[:5]])}

Your Task:
1. Identify what objects/concepts the student drew
2. Determine if the drawing matches the topic "{topic_data['name']}"
3. Provide educational feedback in {age_instruction}
4. Rate the drawing's accuracy (1-10) for capturing the concept
5. Suggest 1-2 improvements
6. Share one fun fact related to the topic

Respond ONLY with valid JSON (no markdown, no extra text):
{{
  "detected_objects": ["object1", "object2", "..."],
  "recognized_concepts": ["concept1", "concept2"],
  "topic_match": "{topic}" or "other_topic_name",
  "confidence_score": 0.85,
  "feedback_text": "2-3 sentences of educational feedback...",
  "accuracy_score": 8,
  "suggestions": ["suggestion 1", "suggestion 2"],
  "fun_fact": "An interesting fact..."
}}"""

        try:
            messages = [
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                    }
                ]}
            ]

            response = self._make_openai_call(
                messages=messages,
                max_tokens=800,
                temperature=0.7
            )

            # Parse JSON response
            result = json.loads(response)

            logger.info(f"[LearnByDrawing] GPT-4V analysis complete for topic: {topic}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"[LearnByDrawing] JSON parse error: {str(e)}, response: {response}")
            # Return fallback response
            return {
                'detected_objects': [],
                'recognized_concepts': [],
                'topic_match': topic,
                'confidence_score': 0.5,
                'feedback_text': 'Great effort on your drawing! Keep practicing.',
                'accuracy_score': 5,
                'suggestions': ['Try adding more details', 'Label the parts of your drawing'],
                'fun_fact': 'Learning by drawing helps you remember concepts better!'
            }

        except Exception as e:
            logger.error(f"[LearnByDrawing] GPT-4V error: {str(e)}")
            raise

    # ==================== Main Analysis Method ====================

    def analyze_drawing(
        self,
        image_bytes: bytes,
        topic: str,
        age_group: str
    ) -> Dict[str, Any]:
        """
        Full drawing analysis using hybrid approach.

        Stage 1: Azure CV for quick detection (< 1s)
        Stage 2: GPT-4V for educational feedback (2-3s)

        Args:
            image_bytes: PNG image bytes
            topic: Learning topic
            age_group: Student age group

        Returns:
            Complete analysis results
        """
        logger.info(f"[LearnByDrawing] Starting analysis for topic: {topic}, age: {age_group}")

        # Step 1: Azure Computer Vision (fast)
        azure_cv_data = self.analyze_with_azure_cv(image_bytes)

        # Step 2: GPT-4 Vision (detailed)
        gpt4_data = self.analyze_with_gpt4_vision(image_bytes, topic, age_group, azure_cv_data)

        # Combine results
        analysis_result = {
            # GPT-4 Vision results (primary)
            'detected_objects': gpt4_data.get('detected_objects', []),
            'recognized_concepts': gpt4_data.get('recognized_concepts', []),
            'topic_match': gpt4_data.get('topic_match', topic),
            'confidence_score': gpt4_data.get('confidence_score', 0.0),
            'feedback_text': gpt4_data.get('feedback_text', ''),
            'accuracy_score': gpt4_data.get('accuracy_score', 0),
            'suggestions': gpt4_data.get('suggestions', []),
            'fun_fact': gpt4_data.get('fun_fact', ''),

            # Azure CV results (supplementary)
            'azure_cv_tags': azure_cv_data.get('tags', []),
            'azure_cv_description': azure_cv_data.get('description', ''),
            'azure_cv_confidence': azure_cv_data.get('confidence', 0.0),

            # Metadata
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

        logger.info(f"[LearnByDrawing] Analysis complete, accuracy score: {analysis_result['accuracy_score']}/10")
        return analysis_result

    # ==================== Badge System ====================

    def check_badges(
        self,
        drawing_count: int,
        topic: str,
        accuracy_score: int,
        user_topics_summary: List[Dict]
    ) -> List[str]:
        """
        Check if user earned any badges.

        Args:
            drawing_count: Total drawings by user
            topic: Current topic
            accuracy_score: Drawing accuracy score
            user_topics_summary: Summary of user's work by topic

        Returns:
            List of badge names earned
        """
        badges = []

        # First drawing
        if drawing_count == 1:
            badges.append("First Drawing")

        # Topic mastery (5+ drawings with avg score 7+)
        topic_summary = next((t for t in user_topics_summary if t['topic'] == topic), None)
        if topic_summary and topic_summary['drawing_count'] >= 5 and topic_summary['average_score'] >= 7:
            badges.append(f"{topic.replace('_', ' ').title()} Expert")

        # Perfect score
        if accuracy_score >= 9:
            badges.append("Perfect Drawing")

        # Prolific artist (25+ drawings)
        if drawing_count >= 25:
            badges.append("Prolific Artist")

        # Multi-topic learner (5+ different topics)
        if len(user_topics_summary) >= 5:
            badges.append("Multi-Topic Learner")

        return badges
