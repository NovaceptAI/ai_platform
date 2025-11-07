import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.ai_service_base import AIServiceBase

log = logging.getLogger(__name__)

class FlashcardsService(AIServiceBase):
    """
    Service for generating interactive flashcards from document content.
    Creates spaced repetition flashcards for effective memorization.
    """
    
    def __init__(self):
        super().__init__()
        self.service_name = "flashcards"
        
    def get_service_info(self) -> Dict[str, Any]:
        """Return information about the flashcards service."""
        return {
            "service_name": self.service_name,
            "description": "Service for generating interactive flashcards from document content",
            "capabilities": [
                "concept_flashcards",
                "term_definition_cards", 
                "question_answer_cards",
                "spaced_repetition"
            ],
            "supported_formats": ["basic", "cloze", "image_occlusion"],
            "version": "1.0.0"
        }
        
    def create_flashcards_for_file(self, file_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create flashcards from file content.
        
        Args:
            file_data: Dictionary containing file content and metadata
            options: Optional configuration for flashcard generation
            
        Returns:
            Dict containing generated flashcards and metadata
        """
        try:
            log.info(f"[Flashcards] Creating flashcards for file: {file_data.get('file_name', 'Unknown')}")
            
            config = options or {
                "max_cards": 20,
                "difficulty": "medium",
                "include_definitions": True,
                "include_concepts": True,
                "include_facts": True
            }
            
            # Extract content for flashcard generation
            content = self._prepare_content(file_data)
            
            # Generate different types of flashcards
            flashcards = []
            
            # 1. Definition cards from key terms
            if config.get("include_definitions", True):
                definition_cards = self._create_definition_cards(content, config)
                flashcards.extend(definition_cards)
            
            # 2. Concept cards from main ideas
            if config.get("include_concepts", True):
                concept_cards = self._create_concept_cards(content, config)
                flashcards.extend(concept_cards)
                
            # 3. Fact cards from important information
            if config.get("include_facts", True):
                fact_cards = self._create_fact_cards(content, config)
                flashcards.extend(fact_cards)
            
            # Limit to max cards and add metadata
            max_cards = config.get("max_cards", 20)
            flashcards = flashcards[:max_cards]
            
            # Add spaced repetition metadata
            for i, card in enumerate(flashcards):
                card.update({
                    "id": f"card_{i+1}",
                    "difficulty_rating": 1,  # Start with easiest
                    "next_review": datetime.utcnow().isoformat(),
                    "review_count": 0,
                    "success_count": 0
                })
            
            result = {
                "flashcards": flashcards,
                "metadata": {
                    "total_cards": len(flashcards),
                    "difficulty": config.get("difficulty", "medium"),
                    "types_included": [
                        t for t in ["definitions", "concepts", "facts"] 
                        if config.get(f"include_{t}", True)
                    ]
                },
                "spaced_repetition": {
                    "algorithm": "sm2_simple",
                    "initial_interval": 1,  # days
                    "ease_factor": 2.5
                },
                "created_at": datetime.utcnow().isoformat()
            }
            
            log.info(f"[Flashcards] Created {len(flashcards)} flashcards")
            return result
            
        except Exception as e:
            log.error(f"[Flashcards] Error creating flashcards: {e}")
            raise
    
    def _prepare_content(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and extract content for flashcard generation."""
        
        content = {
            "text": file_data.get("content", ""),
            "summary": file_data.get("summary", ""),
            "topics": file_data.get("topics", []),
            "entities": file_data.get("entities", {}),
            "key_points": file_data.get("key_points", [])
        }
        
        return content
    
    def _create_definition_cards(self, content: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create flashcards for key terms and definitions."""
        
        # Extract entities that could be definitions
        cards = []
        entities = content.get("entities", {})
        
        # Create definition cards from entities
        for entity_type, entity_list in entities.items():
            if entity_type in ["ORG", "PERSON", "PRODUCT", "MISC"]:
                for entity in entity_list[:3]:  # Limit per type
                    if isinstance(entity, dict):
                        term = entity.get("text", "")
                    else:
                        term = str(entity)
                    
                    if term and len(term) > 2:
                        # Generate definition using AI
                        definition = self._generate_definition(term, content["text"])
                        
                        cards.append({
                            "type": "definition",
                            "front": f"What is {term}?",
                            "back": definition,
                            "category": entity_type.lower(),
                            "tags": ["definition", entity_type.lower()]
                        })
        
        return cards[:5]  # Limit definition cards
    
    def _create_concept_cards(self, content: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create flashcards for main concepts."""

        cards = []
        topics = content.get("topics", [])

        # Create concept cards from topics
        for topic in topics[:8]:
            # Extract topic text from various formats
            topic_text = None

            if isinstance(topic, dict):
                # Try to extract text from common dict keys
                topic_text = topic.get('label') or topic.get('text') or topic.get('topic') or topic.get('name')
                # If still None, don't convert dict to string - skip it
                if not topic_text:
                    continue
            elif isinstance(topic, str):
                topic_text = topic
            else:
                topic_text = str(topic)

            # Ensure topic_text is a clean string
            topic_text = str(topic_text).strip() if topic_text else None

            if topic_text and len(topic_text) > 3:
                # Generate concept explanation
                explanation = self._generate_concept_explanation(topic_text, content["text"])

                cards.append({
                    "type": "concept",
                    "front": f"Explain the concept: {topic_text}",
                    "back": explanation,
                    "category": "concept",
                    "tags": ["concept", "main_idea"]
                })

        return cards
    
    def _create_fact_cards(self, content: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create flashcards for important facts."""
        
        cards = []
        key_points = content.get("key_points", [])
        
        # Create fact cards from key points
        for point in key_points[:7]:
            if isinstance(point, dict):
                text = point.get("text", "")
            else:
                text = str(point)
            
            if text and len(text) > 10:
                # Create question-answer pair
                question = self._generate_fact_question(text)
                answer = text[:200]  # Limit answer length
                
                cards.append({
                    "type": "fact",
                    "front": question,
                    "back": answer,
                    "category": "fact",
                    "tags": ["fact", "key_point"]
                })
        
        return cards
    
    def _generate_definition(self, term: str, context: str) -> str:
        """Generate a definition for a term using AI."""
        try:
            prompt = f"""
            Based on the following context, provide a clear, concise definition for "{term}".
            Keep the definition under 100 words and make it educational.

            Context: {context[:1000]}

            Definition of {term}:
            """

            messages = [
                {"role": "user", "content": prompt}
            ]
            response = self._make_openai_call(messages, max_tokens=150)
            return response.strip()

        except Exception as e:
            log.warning(f"[Flashcards] AI definition generation failed for {term}: {e}")
            return f"A key term mentioned in the document: {term}"
    
    def _generate_concept_explanation(self, concept: str, context: str) -> str:
        """Generate an explanation for a concept using AI."""
        try:
            prompt = f"""
            Based on the following context, explain the concept "{concept}" in a clear, educational way.
            Keep the explanation under 150 words and focus on key aspects.

            Context: {context[:1000]}

            Explanation of {concept}:
            """

            messages = [
                {"role": "user", "content": prompt}
            ]
            response = self._make_openai_call(messages, max_tokens=200)
            return response.strip()

        except Exception as e:
            log.warning(f"[Flashcards] AI concept explanation failed for {concept}: {e}")
            return f"A key concept related to {concept} as discussed in the document."
    
    def _generate_fact_question(self, fact: str) -> str:
        """Generate a question for a given fact."""
        try:
            prompt = f"""
            Create a clear, specific question that would have this fact as the answer.
            Keep the question under 50 words and make it precise.

            Fact: {fact}

            Question:
            """

            messages = [
                {"role": "user", "content": prompt}
            ]
            response = self._make_openai_call(messages, max_tokens=100)
            question = response.strip()

            # Fallback if AI fails
            if not question or len(question) < 5:
                question = "What important information is mentioned about this topic?"

            return question

        except Exception as e:
            log.warning(f"[Flashcards] AI question generation failed: {e}")
            return "What important information is mentioned about this topic?"
