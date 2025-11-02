"""
Story Creator Service for Create Stage Learning Path.

This service transforms document analysis into engaging narrative formats to help students 
learn through storytelling and creative content creation.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.services.ai_service_base import AIServiceBase

logger = logging.getLogger(__name__)


class StoryCreatorService(AIServiceBase):
    """Service for transforming document content into narrative story formats."""
    
    def __init__(self):
        super().__init__()
        self.service_name = "StoryCreator"
    
    def create_story(self, file, story_type: str = "educational", narrative_style: str = "engaging", 
                    audience_level: str = "general", creative_elements: bool = True) -> Dict[str, Any]:
        """
        Transform document content into a narrative story format.
        
        Args:
            file: UploadedFile object containing the document to transform
            story_type: Type of story (educational, historical, biographical, fictional, case_study)
            narrative_style: Style of narrative (engaging, formal, conversational, dramatic)
            audience_level: Target audience (elementary, middle_school, high_school, adult)
            creative_elements: Whether to include creative storytelling elements
            
        Returns:
            Dictionary containing the narrative story
        """
        try:
            logger.info(f"Creating {story_type} story for file: {file.filename}")
            
            # Extract and analyze content
            content = self._extract_file_content(file)
            if not content:
                raise ValueError(f"Could not extract content from {file.filename}")
            
            # Analyze content for story elements
            story_analysis = self._analyze_content_for_story(content, story_type)
            
            # Create story structure
            story_structure = self._create_story_structure(story_type, narrative_style, audience_level)
            
            # Generate story sections
            story_sections = {}
            
            # Opening/Hook
            story_sections['opening'] = self._generate_story_opening(
                content, story_type, narrative_style, audience_level
            )
            
            # Character development (if applicable)
            if story_type in ['biographical', 'historical', 'case_study']:
                story_sections['characters'] = self._develop_characters(
                    content, story_type, audience_level
                )
            
            # Setting and context
            story_sections['setting'] = self._create_setting_context(
                content, story_type, narrative_style
            )
            
            # Main narrative sections
            story_sections['narrative_arc'] = self._generate_narrative_arc(
                content, story_type, narrative_style, audience_level, creative_elements
            )
            
            # Climax/Key learning moments
            story_sections['climax'] = self._generate_story_climax(
                content, story_type, audience_level
            )
            
            # Resolution and lessons
            story_sections['resolution'] = self._generate_story_resolution(
                content, story_type, audience_level
            )
            
            # Educational takeaways
            story_sections['learning_objectives'] = self._extract_learning_objectives(
                content, story_type, audience_level
            )
            
            # Creative elements (if enabled)
            if creative_elements:
                story_sections['creative_elements'] = self._add_creative_elements(
                    content, story_type, narrative_style, audience_level
                )
            
            # Format the complete story
            formatted_story = self._format_complete_story(
                story_sections, story_structure, story_type, narrative_style
            )
            
            # Create storytelling guidelines
            storytelling_guide = self._create_storytelling_guidelines(
                story_type, narrative_style, audience_level
            )
            
            # Generate story metadata
            story_metadata = self._create_story_metadata(
                file, story_type, narrative_style, audience_level, creative_elements
            )
            
            logger.info(f"Successfully created {story_type} story for {file.filename}")
            
            return {
                'story_content': formatted_story,
                'story_structure': story_structure,
                'storytelling_guidelines': storytelling_guide,
                'metadata': story_metadata,
                'story_analysis': story_analysis,
                'story_summary': {
                    'story_type': story_type,
                    'narrative_style': narrative_style,
                    'audience_level': audience_level,
                    'estimated_reading_time': self._estimate_reading_time(formatted_story),
                    'educational_value': self._assess_educational_value(story_sections),
                    'creative_elements_included': creative_elements
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating story for {file.filename}: {str(e)}")
            raise
    
    def _analyze_content_for_story(self, content: str, story_type: str) -> Dict[str, Any]:
        """Analyze content to identify story-worthy elements."""
        
        prompt = f"""
        Analyze the following content to identify elements suitable for a {story_type} story.
        
        Identify:
        - Key characters or figures (people, organizations, concepts)
        - Important events or processes in chronological order
        - Conflicts, challenges, or problems presented
        - Resolutions or outcomes
        - Educational themes and lessons
        - Emotional moments or turning points
        - Setting information (time, place, context)
        
        Content to analyze:
        {content[:3000]}
        
        Provide a structured analysis of story elements.
        """
        
        analysis_response = self._query_ai_service(prompt, max_tokens=600)
        
        return {
            'content_analysis': analysis_response,
            'story_potential': 'high',  # Could be enhanced with sentiment analysis
            'identified_elements': ['characters', 'conflict', 'resolution']  # Could be parsed from response
        }
    
    def _create_story_structure(self, story_type: str, narrative_style: str, audience_level: str) -> Dict[str, Any]:
        """Create the structural framework for the story."""
        
        base_structure = {
            'format': 'narrative_story',
            'has_dialogue': narrative_style in ['engaging', 'conversational', 'dramatic'],
            'includes_emotions': True,
            'visual_descriptions': audience_level in ['elementary', 'middle_school']
        }
        
        if story_type == "educational":
            structure = {
                **base_structure,
                'sections': [
                    'engaging_hook',
                    'character_introduction',
                    'problem_presentation',
                    'discovery_journey',
                    'learning_climax',
                    'resolution_with_lessons'
                ]
            }
        elif story_type == "historical":
            structure = {
                **base_structure,
                'sections': [
                    'historical_setting',
                    'key_figures',
                    'rising_action',
                    'historical_climax',
                    'consequences',
                    'historical_significance'
                ]
            }
        elif story_type == "biographical":
            structure = {
                **base_structure,
                'sections': [
                    'early_life_hook',
                    'formative_experiences',
                    'challenges_faced',
                    'achievements_breakthroughs',
                    'legacy_impact'
                ]
            }
        elif story_type == "case_study":
            structure = {
                **base_structure,
                'sections': [
                    'scenario_introduction',
                    'stakeholders_characters',
                    'problem_analysis',
                    'solution_development',
                    'outcome_evaluation',
                    'lessons_learned'
                ]
            }
        else:  # fictional
            structure = {
                **base_structure,
                'sections': [
                    'world_building',
                    'character_development',
                    'conflict_introduction',
                    'adventure_journey',
                    'climactic_resolution',
                    'theme_revelation'
                ]
            }
        
        return structure
    
    def _generate_story_opening(self, content: str, story_type: str, narrative_style: str, audience_level: str) -> Dict[str, Any]:
        """Generate an engaging story opening."""
        
        style_guidance = {
            'engaging': 'Start with action, dialogue, or a compelling question',
            'formal': 'Begin with context and background information',
            'conversational': 'Open as if talking directly to the reader',
            'dramatic': 'Start with tension, conflict, or a pivotal moment'
        }
        
        audience_guidance = {
            'elementary': 'Simple language, vivid imagery, relatable scenarios',
            'middle_school': 'Age-appropriate complexity, some advanced vocabulary',
            'high_school': 'Sophisticated concepts, analytical thinking elements',
            'adult': 'Complex themes, professional or academic language'
        }
        
        prompt = f"""
        Write an engaging opening for a {story_type} story in {narrative_style} style for {audience_level} audience.
        
        Opening guidelines:
        - Style: {style_guidance[narrative_style]}
        - Audience: {audience_guidance[audience_level]}
        - Length: 150-250 words
        - Hook the reader immediately
        - Introduce the main theme or conflict subtly
        
        Base the opening on this content:
        {content[:2000]}
        
        Create a compelling story opening that draws readers in.
        """
        
        opening_response = self._query_ai_service(prompt, max_tokens=400)
        
        return {
            'title': 'Story Opening',
            'content': opening_response,
            'purpose': 'engage_and_hook',
            'word_count': len(opening_response.split())
        }
    
    def _develop_characters(self, content: str, story_type: str, audience_level: str) -> Dict[str, Any]:
        """Develop characters based on content analysis."""
        
        prompt = f"""
        Develop compelling characters for a {story_type} story at {audience_level} level.
        
        Character development should include:
        - Main characters with clear motivations
        - Supporting characters that advance the story
        - Character backgrounds and personalities
        - Relationships between characters
        - Character growth arcs
        
        Base characters on:
        {content[:2500]}
        
        Create vivid, relatable characters that serve the educational purpose.
        """
        
        characters_response = self._query_ai_service(prompt, max_tokens=500)
        
        return {
            'title': 'Character Development',
            'content': characters_response,
            'purpose': 'character_building',
            'word_count': len(characters_response.split())
        }
    
    def _create_setting_context(self, content: str, story_type: str, narrative_style: str) -> Dict[str, Any]:
        """Create vivid setting and context."""
        
        prompt = f"""
        Create a rich setting and context for a {story_type} story in {narrative_style} style.
        
        Setting should include:
        - Time and place details
        - Atmospheric descriptions
        - Cultural or historical context
        - Environmental factors that affect the story
        - Sensory details that bring the setting to life
        
        Base setting on:
        {content[:2000]}
        
        Create an immersive setting that supports the narrative.
        """
        
        setting_response = self._query_ai_service(prompt, max_tokens=400)
        
        return {
            'title': 'Setting and Context',
            'content': setting_response,
            'purpose': 'world_building',
            'word_count': len(setting_response.split())
        }
    
    def _generate_narrative_arc(self, content: str, story_type: str, narrative_style: str, 
                              audience_level: str, creative_elements: bool) -> Dict[str, Any]:
        """Generate the main narrative arc with multiple sections."""
        
        sections = []
        
        # Create 3-5 main narrative sections
        section_themes = self._identify_narrative_themes(content, story_type)
        
        for i, theme in enumerate(section_themes):
            prompt = f"""
            Write a narrative section for a {story_type} story focusing on: {theme}
            
            Section requirements:
            - Style: {narrative_style}
            - Audience: {audience_level}
            - Include creative elements: {creative_elements}
            - Build on previous sections
            - Advance the plot and character development
            - Include educational elements naturally
            - 200-400 words
            
            Base this section on:
            {content[i*1000:(i+1)*2000]}
            
            Write an engaging narrative section.
            """
            
            section_response = self._query_ai_service(prompt, max_tokens=600)
            
            sections.append({
                'title': f"Chapter {i+1}: {theme}",
                'content': section_response,
                'theme': theme,
                'word_count': len(section_response.split())
            })
        
        return {
            'title': 'Main Narrative',
            'sections': sections,
            'purpose': 'story_development',
            'total_word_count': sum(s['word_count'] for s in sections)
        }
    
    def _generate_story_climax(self, content: str, story_type: str, audience_level: str) -> Dict[str, Any]:
        """Generate the story climax or key learning moment."""
        
        prompt = f"""
        Write the climax or key learning moment for a {story_type} story at {audience_level} level.
        
        Climax should:
        - Resolve the main conflict or challenge
        - Deliver the key educational insight
        - Be emotionally engaging
        - Show character growth or learning
        - Connect to the main themes
        
        Base the climax on:
        {content[:2500]}
        
        Create a powerful, educational climax that delivers the story's main message.
        """
        
        climax_response = self._query_ai_service(prompt, max_tokens=500)
        
        return {
            'title': 'Story Climax',
            'content': climax_response,
            'purpose': 'climax_resolution',
            'word_count': len(climax_response.split())
        }
    
    def _generate_story_resolution(self, content: str, story_type: str, audience_level: str) -> Dict[str, Any]:
        """Generate story resolution and wrap-up."""
        
        prompt = f"""
        Write a satisfying resolution for a {story_type} story at {audience_level} level.
        
        Resolution should:
        - Tie up loose ends
        - Show the impact of learning
        - Connect to real-world applications
        - Leave readers with clear takeaways
        - Inspire further learning or action
        
        Base resolution on:
        {content[:2000]}
        
        Create a meaningful resolution that reinforces the educational goals.
        """
        
        resolution_response = self._query_ai_service(prompt, max_tokens=400)
        
        return {
            'title': 'Story Resolution',
            'content': resolution_response,
            'purpose': 'resolution_closure',
            'word_count': len(resolution_response.split())
        }
    
    def _extract_learning_objectives(self, content: str, story_type: str, audience_level: str) -> Dict[str, Any]:
        """Extract and format learning objectives from the story."""
        
        prompt = f"""
        Extract key learning objectives and educational takeaways from this content for a {story_type} story.
        
        Learning objectives should:
        - Be clear and actionable
        - Appropriate for {audience_level} level
        - Connect to the story narrative
        - Inspire further exploration
        - Be measurable or observable
        
        Content to analyze:
        {content[:2500]}
        
        Provide clear, engaging learning objectives that emerge from the story.
        """
        
        objectives_response = self._query_ai_service(prompt, max_tokens=400)
        
        return {
            'title': 'Learning Objectives',
            'content': objectives_response,
            'purpose': 'educational_outcomes',
            'word_count': len(objectives_response.split())
        }
    
    def _add_creative_elements(self, content: str, story_type: str, narrative_style: str, audience_level: str) -> Dict[str, Any]:
        """Add creative storytelling elements."""
        
        prompt = f"""
        Add creative storytelling elements to enhance a {story_type} story in {narrative_style} style.
        
        Creative elements might include:
        - Dialogue that brings concepts to life
        - Metaphors and analogies
        - Sensory descriptions
        - Emotional moments
        - Plot twists or surprises
        - Interactive elements or questions
        
        Audience level: {audience_level}
        
        Base creative elements on:
        {content[:2000]}
        
        Suggest creative enhancements that make learning more engaging.
        """
        
        creative_response = self._query_ai_service(prompt, max_tokens=400)
        
        return {
            'title': 'Creative Elements',
            'content': creative_response,
            'purpose': 'creative_enhancement',
            'word_count': len(creative_response.split())
        }
    
    def _format_complete_story(self, sections: Dict[str, Any], structure: Dict[str, Any], 
                             story_type: str, narrative_style: str) -> Dict[str, Any]:
        """Format the complete story with proper structure."""
        
        formatted_story = {
            'title': f"{story_type.title()} Story",
            'subtitle': f"A {narrative_style} narrative for learning",
            'story_type': story_type,
            'narrative_style': narrative_style,
            'creation_date': datetime.now().strftime("%B %d, %Y"),
            'story_sections': {}
        }
        
        # Add sections in story order
        section_order = structure.get('sections', [])
        
        for section_key in section_order:
            if section_key in ['engaging_hook', 'historical_setting', 'early_life_hook', 'scenario_introduction', 'world_building'] and 'opening' in sections:
                formatted_story['story_sections']['opening'] = sections['opening']
            elif section_key in ['character_introduction', 'key_figures', 'stakeholders_characters'] and 'characters' in sections:
                formatted_story['story_sections']['characters'] = sections['characters']
            elif 'setting' in sections:
                formatted_story['story_sections']['setting'] = sections['setting']
        
        # Add main narrative arc
        if 'narrative_arc' in sections:
            formatted_story['story_sections']['main_narrative'] = sections['narrative_arc']
        
        # Add climax and resolution
        if 'climax' in sections:
            formatted_story['story_sections']['climax'] = sections['climax']
        if 'resolution' in sections:
            formatted_story['story_sections']['resolution'] = sections['resolution']
        
        # Add educational elements
        if 'learning_objectives' in sections:
            formatted_story['story_sections']['learning_objectives'] = sections['learning_objectives']
        
        # Add creative elements if present
        if 'creative_elements' in sections:
            formatted_story['story_sections']['creative_elements'] = sections['creative_elements']
        
        return formatted_story
    
    def _create_storytelling_guidelines(self, story_type: str, narrative_style: str, audience_level: str) -> Dict[str, Any]:
        """Create guidelines for presenting the story."""
        
        return {
            'presentation_tips': {
                'reading_pace': 'moderate' if audience_level in ['elementary', 'middle_school'] else 'natural',
                'emphasis_points': 'learning moments and key insights',
                'interaction_opportunities': 'discussion questions and reflection prompts',
                'visual_aids': 'recommended for younger audiences'
            },
            'adaptation_suggestions': {
                'for_different_audiences': f'Can be adapted from {audience_level} to other levels',
                'multimedia_options': 'Consider audio narration or visual storytelling',
                'follow_up_activities': 'Discussion, creative projects, further research'
            },
            'educational_integration': {
                'curriculum_connections': 'Identify subject area alignments',
                'assessment_opportunities': 'Comprehension and application questions',
                'extension_activities': 'Creative projects and deeper exploration'
            }
        }
    
    def _create_story_metadata(self, file, story_type: str, narrative_style: str, 
                             audience_level: str, creative_elements: bool) -> Dict[str, Any]:
        """Create metadata for the generated story."""
        
        return {
            'source_file': {
                'filename': file.filename,
                'file_type': file.file_type,
                'file_size': getattr(file, 'file_size', 'unknown')
            },
            'story_configuration': {
                'story_type': story_type,
                'narrative_style': narrative_style,
                'audience_level': audience_level,
                'creative_elements_enabled': creative_elements,
                'generated_at': datetime.now().isoformat(),
                'service_version': '1.0'
            },
            'educational_value': {
                'learning_approach': 'narrative_based',
                'engagement_level': 'high',
                'retention_potential': 'enhanced_through_story',
                'creativity_factor': 'high' if creative_elements else 'moderate'
            }
        }
    
    def _identify_narrative_themes(self, content: str, story_type: str) -> List[str]:
        """Identify main themes for narrative sections."""
        
        # This could be enhanced with more sophisticated content analysis
        themes = {
            'educational': ['Discovery', 'Challenge', 'Learning', 'Application', 'Mastery'],
            'historical': ['Setting the Stage', 'Rising Tensions', 'Key Events', 'Turning Point', 'Legacy'],
            'biographical': ['Early Influences', 'Formative Years', 'Major Challenges', 'Breakthrough Moments', 'Lasting Impact'],
            'case_study': ['Problem Identification', 'Analysis Phase', 'Solution Development', 'Implementation', 'Results'],
            'fictional': ['World Introduction', 'Character Journey', 'Conflict Development', 'Adventure Peak', 'Resolution']
        }
        
        return themes.get(story_type, ['Beginning', 'Development', 'Climax', 'Resolution'])[:4]
    
    def _estimate_reading_time(self, formatted_story: Dict[str, Any]) -> str:
        """Estimate reading time for the story."""
        total_words = 0
        
        sections = formatted_story.get('story_sections', {})
        for section in sections.values():
            if isinstance(section, dict) and 'content' in section:
                total_words += len(section['content'].split())
            elif isinstance(section, dict) and 'sections' in section:
                for subsection in section['sections']:
                    total_words += len(subsection.get('content', '').split())
        
        # Average reading speed: 200-250 words per minute
        minutes = total_words / 225
        
        if minutes < 1:
            return "Less than 1 minute"
        elif minutes < 60:
            return f"{int(minutes)} minutes"
        else:
            hours = int(minutes / 60)
            remaining_minutes = int(minutes % 60)
            return f"{hours}h {remaining_minutes}m"
    
    def _assess_educational_value(self, story_sections: Dict[str, Any]) -> str:
        """Assess the educational value of the story."""
        
        # Simple assessment based on presence of educational elements
        educational_indicators = 0
        
        if 'learning_objectives' in story_sections:
            educational_indicators += 2
        if 'characters' in story_sections:
            educational_indicators += 1
        if 'climax' in story_sections:
            educational_indicators += 1
        if 'creative_elements' in story_sections:
            educational_indicators += 1
        
        if educational_indicators >= 4:
            return "high"
        elif educational_indicators >= 2:
            return "medium"
        else:
            return "basic"
