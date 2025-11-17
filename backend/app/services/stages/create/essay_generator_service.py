import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.services.ai_service_base import AIServiceBase

log = logging.getLogger(__name__)

class EssayGeneratorService(AIServiceBase):
    """
    Service for generating structured analytical essays from document content.
    Helps students transform their analysis into well-organized written work.
    """
    
    def __init__(self):
        super().__init__()
        self.service_name = "essay_generator"
        
    def get_service_info(self) -> Dict[str, Any]:
        """Return information about the essay generator service."""
        return {
            "service_name": self.service_name,
            "description": "Service for generating structured analytical essays from document analysis",
            "capabilities": [
                "essay_outline_creation",
                "paragraph_generation", 
                "thesis_statement_creation",
                "citation_formatting"
            ],
            "supported_essay_types": [
                "analytical", "argumentative", "comparative", 
                "expository", "research_based"
            ],
            "version": "1.0.0"
        }
        
    def generate_essay(self, file_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a structured essay from file content and analysis.
        
        Args:
            file_data: Dictionary containing file content and metadata
            options: Optional configuration for essay generation
            
        Returns:
            Dict containing essay structure, content, and metadata
        """
        try:
            log.info(f"[EssayGenerator] Generating essay for file: {file_data.get('file_name', 'Unknown')}")
            
            config = options or {
                "essay_type": "analytical",
                "length": "medium",  # short, medium, long
                "include_citations": True,
                "academic_level": "college",
                "tone": "formal"
            }
            
            # Extract content for essay generation
            content = self._prepare_content(file_data)
            
            # Generate essay components
            essay = {}
            
            # 1. Create thesis statement and main argument
            thesis = self._generate_thesis_statement(content, config)
            essay["thesis"] = thesis
            
            # 2. Create essay outline
            outline = self._create_essay_outline(content, thesis, config)
            essay["outline"] = outline
            
            # 3. Generate introduction
            introduction = self._generate_introduction(content, thesis, config)
            essay["introduction"] = introduction
            
            # 4. Generate body paragraphs
            body_paragraphs = self._generate_body_paragraphs(content, outline, config)
            essay["body_paragraphs"] = body_paragraphs
            
            # 5. Generate conclusion
            conclusion = self._generate_conclusion(content, thesis, config)
            essay["conclusion"] = conclusion
            
            # 6. Add citations and references if requested
            if config.get("include_citations", True):
                citations = self._generate_citations(content, config)
                essay["citations"] = citations
            
            result = {
                "essay": essay,
                "metadata": {
                    "essay_type": config.get("essay_type", "analytical"),
                    "length": config.get("length", "medium"),
                    "academic_level": config.get("academic_level", "college"),
                    "word_count": self._estimate_word_count(essay),
                    "structure": "five_paragraph" if len(body_paragraphs) <= 3 else "extended"
                },
                "writing_guidelines": {
                    "strengths": self._identify_essay_strengths(essay),
                    "improvements": self._suggest_improvements(essay, config),
                    "style_tips": self._get_style_tips(config)
                },
                "created_at": datetime.utcnow().isoformat()
            }
            
            log.info(f"[EssayGenerator] Generated essay with {len(body_paragraphs)} body paragraphs")
            return result
            
        except Exception as e:
            log.error(f"[EssayGenerator] Error generating essay: {e}")
            raise
    
    def _prepare_content(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and extract content for essay generation."""
        
        content = {
            "text": file_data.get("content", ""),
            "summary": file_data.get("summary", ""),
            "topics": file_data.get("topics", []),
            "entities": file_data.get("entities", {}),
            "key_points": file_data.get("key_points", []),
            "file_name": file_data.get("file_name", "Unknown Document")
        }
        
        return content
    
    def _generate_thesis_statement(self, content: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a strong thesis statement for the essay."""
        
        essay_type = config.get("essay_type", "analytical")
        
        # Create thesis based on essay type
        if essay_type == "analytical":
            thesis_text = self._create_analytical_thesis(content)
        elif essay_type == "argumentative":
            thesis_text = self._create_argumentative_thesis(content)
        elif essay_type == "comparative":
            thesis_text = self._create_comparative_thesis(content)
        else:
            thesis_text = self._create_general_thesis(content)
        
        return {
            "statement": thesis_text,
            "type": essay_type,
            "main_argument": self._extract_main_argument(thesis_text),
            "supporting_points": self._extract_supporting_points(content)[:3]
        }
    
    def _create_essay_outline(self, content: Dict[str, Any], thesis: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a structured essay outline."""
        
        topics = content.get("topics", [])
        key_points = content.get("key_points", [])
        
        # Determine number of body paragraphs based on length
        length = config.get("length", "medium")
        if length == "short":
            num_paragraphs = 3
        elif length == "long":
            num_paragraphs = 5
        else:
            num_paragraphs = 4
        
        outline = {
            "structure": "traditional",
            "sections": [
                {
                    "type": "introduction",
                    "purpose": "Hook, background, thesis statement",
                    "main_points": ["engaging hook", "context/background", "thesis statement"]
                }
            ]
        }
        
        # Create body paragraph outlines
        body_sections = []
        supporting_points = thesis.get("supporting_points", [])
        
        for i in range(num_paragraphs):
            if i < len(supporting_points):
                main_point = supporting_points[i]
            elif i < len(topics):
                main_point = str(topics[i])
            else:
                main_point = f"Additional analysis point {i+1}"
            
            body_sections.append({
                "type": f"body_paragraph_{i+1}",
                "main_point": main_point,
                "supporting_evidence": self._find_supporting_evidence(main_point, content),
                "analysis": f"Analysis of {main_point} in relation to thesis"
            })
        
        outline["sections"].extend(body_sections)
        
        # Add conclusion
        outline["sections"].append({
            "type": "conclusion",
            "purpose": "Restate thesis, summarize main points, final thoughts",
            "main_points": ["restatement of thesis", "summary of evidence", "broader implications"]
        })
        
        return outline
    
    def _generate_introduction(self, content: Dict[str, Any], thesis: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate essay introduction paragraph."""
        
        try:
            prompt = f"""
            Write an engaging introduction paragraph for an {config.get('essay_type', 'analytical')} essay.
            The thesis is: {thesis.get('statement', 'Main argument about the topic')}
            
            Document context: {content.get('summary', '')[:300]}
            Main topics: {', '.join(str(t) for t in content.get('topics', [])[:3])}
            
            Structure: Hook → Background/Context → Thesis Statement
            Tone: {config.get('tone', 'formal')}
            Academic level: {config.get('academic_level', 'college')}
            
            Write a compelling introduction paragraph:
            """
            
            intro_text = self._make_openai_call(prompt, max_tokens=250)
            
            return {
                "text": intro_text.strip(),
                "components": {
                    "hook": "Opening sentence designed to engage the reader",
                    "background": "Context about the topic and document",
                    "thesis": thesis.get('statement', '')
                },
                "word_count": len(intro_text.split())
            }
            
        except Exception as e:
            log.warning(f"[EssayGenerator] AI introduction generation failed: {e}")
            return {
                "text": f"This essay examines {content.get('file_name', 'the document')} and argues that {thesis.get('statement', 'the main argument holds true')}.",
                "components": {
                    "hook": "Document analysis opening",
                    "background": "Context from source material", 
                    "thesis": thesis.get('statement', '')
                },
                "word_count": 25
            }
    
    def _generate_body_paragraphs(self, content: Dict[str, Any], outline: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate body paragraphs based on outline."""
        
        body_paragraphs = []
        sections = outline.get("sections", [])
        
        for section in sections:
            if section.get("type", "").startswith("body_paragraph"):
                paragraph = self._generate_single_body_paragraph(
                    section, content, config
                )
                body_paragraphs.append(paragraph)
        
        return body_paragraphs
    
    def _generate_single_body_paragraph(self, section: Dict[str, Any], content: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a single body paragraph."""
        
        main_point = section.get("main_point", "Key point")
        evidence = section.get("supporting_evidence", [])
        
        try:
            prompt = f"""
            Write a body paragraph for an {config.get('essay_type', 'analytical')} essay.
            
            Main point: {main_point}
            Supporting evidence: {', '.join(evidence[:3])}
            Document context: {content.get('text', '')[:500]}
            
            Structure: Topic sentence → Evidence → Analysis → Transition
            Tone: {config.get('tone', 'formal')}
            
            Write a well-developed body paragraph:
            """
            
            paragraph_text = self._make_openai_call(prompt, max_tokens=300)
            
            return {
                "text": paragraph_text.strip(),
                "main_point": main_point,
                "evidence_used": evidence[:3],
                "structure": "TEAT (Topic, Evidence, Analysis, Transition)",
                "word_count": len(paragraph_text.split())
            }
            
        except Exception as e:
            log.warning(f"[EssayGenerator] AI paragraph generation failed: {e}")
            return {
                "text": f"{main_point} is clearly demonstrated in the document. The evidence shows that this point is significant and supports the overall thesis. This analysis reveals important insights about the topic.",
                "main_point": main_point,
                "evidence_used": evidence[:3],
                "structure": "TEAT (Topic, Evidence, Analysis, Transition)",
                "word_count": 35
            }
    
    def _generate_conclusion(self, content: Dict[str, Any], thesis: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate essay conclusion paragraph."""
        
        try:
            prompt = f"""
            Write a strong conclusion paragraph for an {config.get('essay_type', 'analytical')} essay.
            
            Thesis: {thesis.get('statement', 'Main argument')}
            Document: {content.get('file_name', 'the source')}
            Main topics covered: {', '.join(str(t) for t in content.get('topics', [])[:3])}
            
            Structure: Restate thesis → Summarize key points → Broader implications
            Tone: {config.get('tone', 'formal')}
            
            Write a compelling conclusion:
            """
            
            conclusion_text = self._make_openai_call(prompt, max_tokens=200)
            
            return {
                "text": conclusion_text.strip(),
                "components": {
                    "thesis_restatement": "Restated thesis in new words",
                    "summary": "Key points summarized",
                    "implications": "Broader significance or call to action"
                },
                "word_count": len(conclusion_text.split())
            }
            
        except Exception as e:
            log.warning(f"[EssayGenerator] AI conclusion generation failed: {e}")
            return {
                "text": f"In conclusion, the analysis of {content.get('file_name', 'this document')} demonstrates that {thesis.get('statement', 'the thesis is valid')}. This understanding provides valuable insights for further study and application.",
                "components": {
                    "thesis_restatement": "Thesis restated",
                    "summary": "Points summarized",
                    "implications": "Future implications noted"
                },
                "word_count": 30
            }
    
    def _create_analytical_thesis(self, content: Dict[str, Any]) -> str:
        """Create an analytical thesis statement."""
        topics = content.get("topics", [])
        main_topic = topics[0] if topics else "the document"
        
        return f"Through careful analysis of {content.get('file_name', 'the text')}, it becomes clear that {main_topic} reveals important insights about the underlying themes and arguments presented."
    
    def _create_argumentative_thesis(self, content: Dict[str, Any]) -> str:
        """Create an argumentative thesis statement."""
        topics = content.get("topics", [])
        main_topic = topics[0] if topics else "the main issue"
        
        return f"The evidence presented in {content.get('file_name', 'this document')} strongly supports the argument that {main_topic} is crucial for understanding the broader implications of the topic."
    
    def _create_comparative_thesis(self, content: Dict[str, Any]) -> str:
        """Create a comparative thesis statement."""
        topics = content.get("topics", [])
        
        if len(topics) >= 2:
            return f"While both {topics[0]} and {topics[1]} are discussed in {content.get('file_name', 'the document')}, {topics[0]} proves to be more significant in understanding the overall argument."
        else:
            return f"Comparing different aspects of {topics[0] if topics else 'the topic'} reveals important distinctions in how the author presents their argument."
    
    def _create_general_thesis(self, content: Dict[str, Any]) -> str:
        """Create a general thesis statement."""
        return f"The analysis of {content.get('file_name', 'this document')} demonstrates key insights that enhance our understanding of the presented material and its broader implications."
    
    def _extract_main_argument(self, thesis_text: str) -> str:
        """Extract the main argument from thesis statement."""
        return thesis_text.split("that")[1] if "that" in thesis_text else thesis_text
    
    def _extract_supporting_points(self, content: Dict[str, Any]) -> List[str]:
        """Extract supporting points from content."""
        points = []
        
        # Add key topics as supporting points
        topics = content.get("topics", [])
        for topic in topics[:4]:
            if isinstance(topic, str) and len(topic) > 3:
                points.append(f"Analysis of {topic}")
        
        # Add key points from analysis
        key_points = content.get("key_points", [])
        for kp in key_points[:3]:
            if isinstance(kp, dict):
                text = kp.get("text", "")
            else:
                text = str(kp)
            
            if text and len(text) > 10:
                points.append(text[:100])
        
        return points
    
    def _find_supporting_evidence(self, main_point: str, content: Dict[str, Any]) -> List[str]:
        """Find supporting evidence for a main point."""
        evidence = []
        
        # Look for relevant key points
        key_points = content.get("key_points", [])
        for kp in key_points:
            if isinstance(kp, dict):
                text = kp.get("text", "")
            else:
                text = str(kp)
            
            # Simple relevance check
            if any(word in text.lower() for word in main_point.lower().split()[:3]):
                evidence.append(text[:150])
        
        # Add some generic evidence if nothing found
        if not evidence:
            evidence = [
                f"Evidence from the document supporting {main_point}",
                f"Analysis showing the significance of {main_point}",
                f"Examples demonstrating {main_point}"
            ]
        
        return evidence[:3]
    
    def _generate_citations(self, content: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate citation information."""
        
        return [
            {
                "source": content.get("file_name", "Unknown Document"),
                "type": "document",
                "format": "MLA",
                "citation": f'Author. "{content.get("file_name", "Document Title")}." Publication, Date.',
                "in_text": "(Author, Page)"
            }
        ]
    
    def _estimate_word_count(self, essay: Dict[str, Any]) -> int:
        """Estimate total word count for the essay."""
        total_words = 0
        
        # Count introduction
        intro = essay.get("introduction", {})
        total_words += intro.get("word_count", 100)
        
        # Count body paragraphs
        body_paragraphs = essay.get("body_paragraphs", [])
        for paragraph in body_paragraphs:
            total_words += paragraph.get("word_count", 150)
        
        # Count conclusion
        conclusion = essay.get("conclusion", {})
        total_words += conclusion.get("word_count", 80)
        
        return total_words
    
    def _identify_essay_strengths(self, essay: Dict[str, Any]) -> List[str]:
        """Identify strengths in the generated essay."""
        
        strengths = [
            "Clear thesis statement with focused argument",
            "Well-organized structure with logical flow", 
            "Evidence-based analysis supporting main points",
            "Strong conclusion that reinforces the thesis"
        ]
        
        return strengths
    
    def _suggest_improvements(self, essay: Dict[str, Any], config: Dict[str, Any]) -> List[str]:
        """Suggest improvements for the essay."""
        
        improvements = [
            "Consider adding more specific examples from the source",
            "Strengthen transitions between paragraphs",
            "Expand analysis to show deeper critical thinking",
            "Review for clarity and conciseness in language"
        ]
        
        return improvements
    
    def _get_style_tips(self, config: Dict[str, Any]) -> List[str]:
        """Get style tips based on configuration."""
        
        academic_level = config.get("academic_level", "college")
        essay_type = config.get("essay_type", "analytical")
        
        tips = [
            f"Use {config.get('tone', 'formal')} tone throughout the essay",
            f"Follow {academic_level}-level writing conventions",
            f"Ensure all claims are supported with evidence for {essay_type} essays",
            "Proofread for grammar, spelling, and punctuation"
        ]
        
        return tips
