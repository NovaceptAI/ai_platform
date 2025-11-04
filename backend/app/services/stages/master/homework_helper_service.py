import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.ai_service_base import AIServiceBase

log = logging.getLogger(__name__)

class HomeworkHelperService(AIServiceBase):
    """
    Service for providing homework assistance and study guidance.
    Helps students understand concepts and solve problems step-by-step.
    """
    
    def __init__(self):
        super().__init__()
        self.service_name = "homework_helper"
        
    def get_service_info(self) -> Dict[str, Any]:
        """Return information about the homework helper service."""
        return {
            "service_name": self.service_name,
            "description": "Service for providing homework assistance and study guidance",
            "capabilities": [
                "step_by_step_explanations",
                "concept_clarification",
                "problem_solving_guidance",
                "study_recommendations"
            ],
            "supported_subjects": ["general", "math", "science", "literature", "history"],
            "version": "1.0.0"
        }
        
    def create_homework_assistance(self, file_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create homework assistance materials from file content.
        
        Args:
            file_data: Dictionary containing file content and metadata
            options: Optional configuration for homework assistance
            
        Returns:
            Dict containing homework help materials and guidance
        """
        try:
            log.info(f"[HomeworkHelper] Creating assistance for file: {file_data.get('file_name', 'Unknown')}")
            
            config = options or {
                "include_explanations": True,
                "include_examples": True,
                "include_practice": True,
                "difficulty_level": "medium"
            }
            
            # Extract content for homework assistance
            content = self._prepare_content(file_data)
            
            # Generate homework assistance materials
            assistance = {}
            
            # 1. Key concept explanations
            if config.get("include_explanations", True):
                explanations = self._create_concept_explanations(content, config)
                assistance["explanations"] = explanations
            
            # 2. Example problems/questions
            if config.get("include_examples", True):
                examples = self._create_example_problems(content, config)
                assistance["examples"] = examples
                
            # 3. Practice recommendations
            if config.get("include_practice", True):
                practice = self._create_practice_recommendations(content, config)
                assistance["practice_recommendations"] = practice
            
            # 4. Study guidance
            study_guidance = self._create_study_guidance(content, config)
            assistance["study_guidance"] = study_guidance
            
            result = {
                "homework_assistance": assistance,
                "metadata": {
                    "difficulty_level": config.get("difficulty_level", "medium"),
                    "subject_area": self._identify_subject_area(content),
                    "total_items": sum(len(v) if isinstance(v, list) else 1 for v in assistance.values())
                },
                "study_plan": {
                    "recommended_order": ["explanations", "examples", "practice_recommendations"],
                    "estimated_time": "30-45 minutes",
                    "difficulty_progression": "basic → intermediate → advanced"
                },
                "created_at": datetime.utcnow().isoformat()
            }
            
            log.info(f"[HomeworkHelper] Created homework assistance with {len(assistance)} sections")
            return result
            
        except Exception as e:
            log.error(f"[HomeworkHelper] Error creating homework assistance: {e}")
            raise
    
    def _prepare_content(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and extract content for homework assistance."""
        
        content = {
            "text": file_data.get("content", ""),
            "summary": file_data.get("summary", ""),
            "topics": file_data.get("topics", []),
            "entities": file_data.get("entities", {}),
            "key_points": file_data.get("key_points", [])
        }
        
        return content
    
    def _create_concept_explanations(self, content: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create step-by-step explanations for key concepts."""
        
        explanations = []
        topics = content.get("topics", [])
        
        # Create explanations for main topics
        for topic in topics[:5]:  # Limit to 5 main topics
            if isinstance(topic, str) and len(topic) > 3:
                explanation = self._generate_concept_explanation(topic, content["text"])
                
                explanations.append({
                    "concept": topic,
                    "explanation": explanation,
                    "difficulty": "medium",
                    "type": "concept_explanation",
                    "estimated_time": "5-10 minutes"
                })
        
        return explanations
    
    def _create_example_problems(self, content: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create example problems and solutions."""
        
        examples = []
        key_points = content.get("key_points", [])
        
        # Create example problems from key points
        for point in key_points[:4]:  # Limit to 4 examples
            if isinstance(point, dict):
                text = point.get("text", "")
            else:
                text = str(point)
            
            if text and len(text) > 20:
                problem = self._generate_example_problem(text, content["text"])
                
                examples.append({
                    "problem": problem["question"],
                    "solution": problem["solution"],
                    "explanation": problem["explanation"],
                    "difficulty": "medium",
                    "type": "example_problem"
                })
        
        return examples
    
    def _create_practice_recommendations(self, content: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create practice recommendations and exercises."""
        
        recommendations = []
        topics = content.get("topics", [])
        
        # Create practice recommendations for each topic
        for topic in topics[:4]:
            if isinstance(topic, str) and len(topic) > 3:
                practice = self._generate_practice_recommendation(topic, content["text"])
                
                recommendations.append({
                    "topic": topic,
                    "practice_activities": practice["activities"],
                    "resources": practice["resources"],
                    "time_estimate": practice["time_estimate"],
                    "difficulty_progression": practice["progression"]
                })
        
        return recommendations
    
    def _create_study_guidance(self, content: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Create overall study guidance and tips."""
        
        subject_area = self._identify_subject_area(content)
        
        guidance = {
            "study_approach": self._get_study_approach(subject_area),
            "key_strategies": [
                "Break down complex concepts into smaller parts",
                "Practice regularly with varied examples",
                "Connect new information to what you already know",
                "Ask questions and seek clarification when needed"
            ],
            "common_mistakes": self._identify_common_mistakes(content, subject_area),
            "success_tips": [
                "Start with understanding, not memorizing",
                "Use multiple learning methods (visual, auditory, kinesthetic)",
                "Take breaks and review regularly",
                "Apply concepts to real-world examples"
            ]
        }
        
        return guidance
    
    def _identify_subject_area(self, content: Dict[str, Any]) -> str:
        """Identify the subject area based on content."""
        
        text = content.get("text", "").lower()
        topics = [str(t).lower() for t in content.get("topics", [])]
        all_text = f"{text} {' '.join(topics)}"
        
        # Simple keyword-based classification
        if any(word in all_text for word in ["math", "equation", "formula", "calculate", "number"]):
            return "mathematics"
        elif any(word in all_text for word in ["science", "experiment", "hypothesis", "theory", "biology", "chemistry", "physics"]):
            return "science"
        elif any(word in all_text for word in ["literature", "poem", "story", "character", "plot", "author"]):
            return "literature"
        elif any(word in all_text for word in ["history", "historical", "century", "war", "civilization", "culture"]):
            return "history"
        else:
            return "general"
    
    def _generate_concept_explanation(self, concept: str, context: str) -> str:
        """Generate a detailed explanation for a concept."""
        try:
            prompt = f"""
            Provide a clear, step-by-step explanation of the concept "{concept}" based on the following context.
            Make it suitable for homework help - educational and easy to understand.
            Include why it's important and how it connects to other ideas.
            Keep it under 200 words.
            
            Context: {context[:1000]}
            
            Explanation of {concept}:
            """
            
            messages = [
                {"role": "system", "content": "You are a helpful homework tutor providing clear explanations."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._make_openai_call(messages, max_tokens=250)
            return response.strip() or f"This concept involves understanding {concept} and its applications in the subject area."
            
        except Exception as e:
            log.warning(f"[HomeworkHelper] AI explanation generation failed for {concept}: {e}")
            return f"This concept involves understanding {concept} and its applications in the subject area."
    
    def _generate_example_problem(self, content: str, context: str) -> Dict[str, str]:
        """Generate an example problem with solution."""
        try:
            prompt = f"""
            Based on this content, create a practice problem that helps students understand the concept.
            Include the question, step-by-step solution, and explanation.
            
            Content: {content[:500]}
            Context: {context[:500]}
            
            Format:
            Question: [clear question]
            Solution: [step-by-step solution]
            Explanation: [why this approach works]
            """
            
            messages = [
                {"role": "system", "content": "You are a helpful homework tutor creating practice problems."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._make_openai_call(messages, max_tokens=300)
            
            # Parse the response
            lines = response.strip().split('\n')
            problem = {
                "question": "Practice applying the concepts from this material.",
                "solution": "Work through the concepts step by step.",
                "explanation": "This helps reinforce understanding of key ideas."
            }
            
            current_section = None
            for line in lines:
                if line.startswith("Question:"):
                    current_section = "question"
                    problem["question"] = line.replace("Question:", "").strip()
                elif line.startswith("Solution:"):
                    current_section = "solution"
                    problem["solution"] = line.replace("Solution:", "").strip()
                elif line.startswith("Explanation:"):
                    current_section = "explanation"
                    problem["explanation"] = line.replace("Explanation:", "").strip()
                elif current_section and line.strip():
                    problem[current_section] += " " + line.strip()
            
            return problem
            
        except Exception as e:
            log.warning(f"[HomeworkHelper] AI problem generation failed: {e}")
            return {
                "question": "Practice applying the concepts from this material.",
                "solution": "Work through the concepts step by step.",
                "explanation": "This helps reinforce understanding of key ideas."
            }
    
    def _generate_practice_recommendation(self, topic: str, context: str) -> Dict[str, Any]:
        """Generate practice recommendations for a topic."""
        
        return {
            "activities": [
                f"Review key concepts related to {topic}",
                f"Practice problems involving {topic}",
                f"Create mind maps or summaries about {topic}",
                f"Discuss {topic} with classmates or teacher"
            ],
            "resources": [
                "Textbook chapters on this topic",
                "Online educational videos",
                "Practice worksheets",
                "Study group discussions"
            ],
            "time_estimate": "20-30 minutes",
            "progression": ["Review basics", "Practice examples", "Apply to new problems", "Teach someone else"]
        }
    
    def _get_study_approach(self, subject_area: str) -> str:
        """Get recommended study approach for subject area."""
        
        approaches = {
            "mathematics": "Focus on understanding formulas and practicing step-by-step problem solving",
            "science": "Combine theoretical understanding with practical examples and experiments",
            "literature": "Analyze texts carefully and connect themes to broader contexts",
            "history": "Study chronologically and understand cause-and-effect relationships",
            "general": "Break down complex topics and use multiple learning strategies"
        }
        
        return approaches.get(subject_area, approaches["general"])
    
    def _identify_common_mistakes(self, content: Dict[str, Any], subject_area: str) -> List[str]:
        """Identify common mistakes for the subject area."""
        
        common_mistakes = {
            "mathematics": [
                "Rushing through calculations without checking work",
                "Not showing all steps in problem solving",
                "Forgetting to include units in answers"
            ],
            "science": [
                "Memorizing without understanding underlying principles",
                "Not connecting theory to practical applications",
                "Overlooking experimental variables and controls"
            ],
            "literature": [
                "Reading for plot only, missing deeper themes",
                "Not supporting arguments with textual evidence",
                "Overlooking literary devices and their purposes"
            ],
            "history": [
                "Memorizing dates without understanding significance",
                "Not considering multiple perspectives on events",
                "Failing to connect historical events to modern times"
            ],
            "general": [
                "Not taking breaks during study sessions",
                "Trying to memorize instead of understand",
                "Not asking for help when confused"
            ]
        }
        
        return common_mistakes.get(subject_area, common_mistakes["general"])
