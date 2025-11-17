"""
Document Visualizer Service for Create Stage Learning Path.

This service analyzes document content and generates visual representations (diagrams, illustrations,
infographics) of the actual content to help students understand concepts through visual learning.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.services.ai_service_base import AIServiceBase
from app.db import db
from app.services.external.azure_image import azure_dalle_generate

logger = logging.getLogger(__name__)


class StoryVisualizerService(AIServiceBase):
    """Service for transforming document content into visual diagrams and illustrations."""

    def __init__(self):
        super().__init__()
        self.service_name = "DocumentVisualizer"

    def get_service_info(self) -> Dict[str, Any]:
        """
        Return information about this service.

        Returns:
            Dictionary with service information
        """
        return {
            'service_name': 'DocumentVisualizer',
            'description': 'Analyzes document content and generates visual representations of concepts, processes, and data',
            'capabilities': [
                'concept_diagrams',
                'process_flowcharts',
                'data_visualizations',
                'technical_illustrations',
                'infographics'
            ],
            'supported_styles': ['vivid', 'natural'],
            'visualization_types': ['diagram', 'flowchart', 'infographic', 'illustration', 'schematic'],
            'version': '2.0'
        }

    def create_story(self, file, story_type: str = "educational", narrative_style: str = "engaging",
                    audience_level: str = "general", creative_elements: bool = True) -> Dict[str, Any]:
        """
        Analyze document content and prepare for visualization.
        This method maintains backward compatibility with the old API.

        Args:
            file: UploadedFile object containing the document to visualize
            story_type: Kept for compatibility (not used)
            narrative_style: Kept for compatibility (not used)
            audience_level: Target audience for visualization complexity
            creative_elements: Kept for compatibility (not used)

        Returns:
            Dictionary containing document analysis ready for visualization
        """
        try:
            logger.info(f"Analyzing document for visualization: {file.original_file_name}")

            # Extract and analyze content
            content = self._extract_file_content(file)
            if not content:
                raise ValueError(f"Could not extract content from {file.original_file_name}")

            # Analyze content for visualizable sections
            content_analysis = self._analyze_content_for_visualization(content)

            # Identify key concepts and sections to visualize
            visualizable_sections = self._identify_visualizable_sections(content, content_analysis)

            # Generate metadata
            metadata = self._create_visualization_metadata(file, audience_level)

            logger.info(f"Successfully analyzed {file.original_file_name} - found {len(visualizable_sections)} visualizable sections")

            return {
                'story_content': {  # Keeping 'story_content' key for backward compatibility
                    'title': f"Visual Guide: {file.original_file_name}",
                    'subtitle': f"Visual representations of document content",
                    'creation_date': datetime.now().strftime("%B %d, %Y"),
                    'story_sections': visualizable_sections  # These are now content sections, not story sections
                },
                'metadata': metadata,
                'content_analysis': content_analysis,
                'story_summary': {  # Kept for backward compatibility
                    'story_type': 'document_visualization',
                    'sections_count': len(visualizable_sections),
                    'audience_level': audience_level
                }
            }

        except Exception as e:
            logger.error(f"Error analyzing document {file.original_file_name}: {str(e)}")
            raise

    def generate_scene_images(self, story_content: Dict[str, Any], num_scenes: int = 5,
                              style: str = "vivid", size: str = "1024x1024") -> List[Dict[str, Any]]:
        """
        Generate visual diagrams/illustrations for key document concepts using DALL-E.

        Args:
            story_content: The document content dictionary (kept name for backward compatibility)
            num_scenes: Number of visualizations to generate (default: 5)
            style: Image style - "vivid" or "natural"
            size: Image size - "1024x1024", "1024x1792", "1792x1024"

        Returns:
            List of visualization dictionaries with images
        """
        try:
            logger.info(f"Generating {num_scenes} document visualizations")

            # Extract content sections
            content_sections = story_content.get('story_sections', {})

            # Identify key sections to visualize
            sections_to_visualize = self._identify_key_visualizable_sections(content_sections, num_scenes)

            visualized_sections = []

            for i, section_data in enumerate(sections_to_visualize, 1):
                try:
                    logger.info(f"Generating visualization {i}/{len(sections_to_visualize)}: {section_data.get('title')}")

                    # Generate image prompt for this content section
                    image_prompt = self._create_visualization_prompt(section_data, style)

                    # Add delay to respect rate limits (except for first image)
                    if i > 1:
                        logger.info(f"Waiting 15s to respect DALL-E rate limits...")
                        time.sleep(15)

                    # Generate image using Azure DALL-E
                    image_results = azure_dalle_generate(
                        prompt=image_prompt,
                        size=size,
                        style=style,
                        quality="standard",
                        n=1
                    )

                    logger.info(f"DALL-E API response for visualization {i}: {image_results}")

                    if image_results and len(image_results) > 0 and image_results[0].get('url'):
                        image_url = image_results[0]['url']

                        visualized_sections.append({
                            'scene_number': i,
                            'title': section_data.get('title', f'Visualization {i}'),
                            'description': section_data.get('content', '')[:500],  # First 500 chars
                            'image_url': image_url,
                            'image_prompt': image_prompt,
                            'revised_prompt': image_results[0].get('revised_prompt'),
                            'style': style,
                            'size': size,
                            'visualization_type': section_data.get('visualization_type', 'diagram')
                        })

                        logger.info(f"✅ Successfully generated visualization {i}")
                    else:
                        logger.warning(f"No image URL returned for visualization {i}")
                        visualized_sections.append({
                            'scene_number': i,
                            'title': section_data.get('title', f'Visualization {i}'),
                            'description': section_data.get('content', '')[:500],
                            'error': 'No image generated',
                            'image_prompt': image_prompt
                        })

                except Exception as e:
                    logger.error(f"Error generating visualization {i}: {str(e)}")
                    visualized_sections.append({
                        'scene_number': i,
                        'title': section_data.get('title', f'Visualization {i}'),
                        'description': section_data.get('content', '')[:500],
                        'error': str(e),
                        'image_prompt': image_prompt if 'image_prompt' in locals() else 'Failed to create prompt'
                    })
                    continue

            logger.info(f"Completed visualization generation: {len([s for s in visualized_sections if 'image_url' in s])}/{len(visualized_sections)} successful")

            return visualized_sections

        except Exception as e:
            logger.error(f"Error in visualization generation: {str(e)}")
            raise

    def _identify_key_visualizable_sections(self, content_sections: Dict[str, Any], num_visualizations: int) -> List[Dict[str, Any]]:
        """Identify the most important content sections to visualize from the document."""
        visualizable_sections = []

        # Iterate through all sections and collect them
        for section_key, section in content_sections.items():
            if isinstance(section, dict):
                visualizable_sections.append({
                    'title': section.get('title', section_key.replace('_', ' ').title()),
                    'content': section.get('content', ''),
                    'visualization_type': section.get('visualization_type', 'diagram'),
                    'concepts': section.get('concepts', [])
                })

        # Return requested number of sections
        return visualizable_sections[:num_visualizations]

    def _create_visualization_prompt(self, section_data: Dict[str, Any], style: str) -> str:
        """Create a DALL-E prompt for visualizing document content as a diagram/illustration."""
        title = section_data.get('title', 'Concept')
        content = section_data.get('content', '')[:1000]  # Limit content length
        visualization_type = section_data.get('visualization_type', 'diagram')

        # Create a factual visual description for the actual content
        prompt_request = f"""
        Based on this document content, create a detailed description for generating an educational diagram or illustration:

        Topic: {title}
        Content: {content}

        Create a precise description (max 200 words) for a {visualization_type} that shows:
        - The actual concepts, processes, or data described in the content
        - Key components and their relationships as stated in the document
        - Factual information presented in visual form (not creative interpretation)
        - Labels, arrows, or connections that illustrate the documented information
        - Clear, educational representation suitable for learning

        IMPORTANT: This should be a literal visual representation of what IS in the document, not a creative story or fictional scene.
        Focus on diagrams, flowcharts, infographics, technical illustrations, or educational graphics.
        Do not add creative elements, characters, or narrative scenes - only factual visual representations.
        """

        # Get AI to create the visualization prompt
        image_description = self._query_ai_service(prompt_request, max_tokens=250, temperature=0.3)

        # Clean up and format the prompt
        image_prompt = image_description.strip()

        # Add style guidance based on visualization type
        if style == "vivid":
            image_prompt += ". Clear educational diagram style with vibrant colors for clarity, labeled components, clean design."
        else:
            image_prompt += ". Professional educational diagram style with natural colors, clear labels, technical illustration quality."

        logger.info(f"Created visualization prompt: {image_prompt[:100]}...")

        return image_prompt

    def _analyze_content_for_visualization(self, content: str) -> Dict[str, Any]:
        """Analyze content to identify visualizable elements."""

        prompt = f"""
        Analyze the following document content to identify sections suitable for visual representation.

        Identify:
        - Key concepts and their definitions
        - Processes, workflows, or sequences described
        - Relationships between ideas or components
        - Data, statistics, or quantitative information
        - Structures, systems, or hierarchies
        - Comparisons or contrasts
        - Cause-and-effect relationships

        Content to analyze:
        {content[:3000]}

        List the main topics/sections that would benefit from diagrams, flowcharts, or illustrations.
        Focus on factual, educational content that can be visualized literally.
        """

        analysis_response = self._query_ai_service(prompt, max_tokens=600, temperature=0.3)

        return {
            'content_analysis': analysis_response,
            'visualization_potential': 'high',
            'content_type': 'educational'
        }

    def _identify_visualizable_sections(self, content: str, content_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Identify key sections of the document that can be visualized."""

        prompt = f"""
        Based on this document content, identify specific sections that would benefit from visual diagrams or illustrations.

        Content:
        {content[:4000]}

        For each visualizable section, provide:
        1. A clear title (e.g., "The Water Cycle Process", "Cell Structure Components")
        2. The specific content/concepts to visualize (2-3 sentences describing what's in the document)
        3. The type of visualization (diagram, flowchart, infographic, illustration, chart)
        4. Key concepts or components (list 3-5 items from the document)

        Identify 3-7 sections. Focus on concrete, factual information that can be represented visually.
        Examples: processes, relationships, structures, data, comparisons, systems, hierarchies.

        IMPORTANT: Base your sections ONLY on what is actually in the document. Do not create fictional scenarios.
        Extract factual content that needs visual explanation.

        Format as:
        Section 1:
        Title: [exact topic from document]
        Content: [what the document says about this]
        Type: [visualization type]
        Concepts: [list actual concepts from document]
        """

        sections_response = self._query_ai_service(prompt, max_tokens=1000, temperature=0.3)

        # Parse the response into structured sections
        sections = self._parse_sections_response(sections_response, content)

        return sections

    def _parse_sections_response(self, sections_response: str, full_content: str) -> Dict[str, Any]:
        """Parse AI response into structured section dictionaries."""
        sections_dict = {}

        # Split response into individual sections
        section_blocks = sections_response.split('Section ')

        section_counter = 0
        for block in section_blocks:
            if not block.strip():
                continue

            try:
                # Extract fields from the block
                lines = block.strip().split('\n')
                section_data = {
                    'title': 'Visualization',
                    'content': '',
                    'visualization_type': 'diagram',
                    'concepts': []
                }

                for line in lines:
                    line = line.strip()
                    if line.startswith('Title:'):
                        section_data['title'] = line.replace('Title:', '').strip()
                    elif line.startswith('Content:'):
                        section_data['content'] = line.replace('Content:', '').strip()
                    elif line.startswith('Type:'):
                        section_data['visualization_type'] = line.replace('Type:', '').strip().lower()
                    elif line.startswith('Concepts:'):
                        concepts_text = line.replace('Concepts:', '').strip()
                        section_data['concepts'] = [c.strip() for c in concepts_text.split(',') if c.strip()]

                # Only add if we have at least a title
                if section_data['title'] and section_data['title'] != 'Visualization':
                    section_counter += 1
                    section_key = f'section_{section_counter}'
                    sections_dict[section_key] = section_data

            except Exception as e:
                logger.warning(f"Error parsing section block: {str(e)}")
                continue

        # If parsing failed, create a default section
        if not sections_dict:
            sections_dict['section_1'] = {
                'title': 'Document Overview',
                'content': full_content[:500],
                'visualization_type': 'diagram',
                'concepts': ['Main concepts from document']
            }

        return sections_dict

    def _create_visualization_metadata(self, file, audience_level: str) -> Dict[str, Any]:
        """Create metadata for the document visualization."""

        return {
            'source_file': {
                'filename': file.original_file_name,
                'file_type': file.file_type,
                'stored_name': file.stored_file_name
            },
            'visualization_config': {
                'service_type': 'document_visualization',
                'audience_level': audience_level,
                'generated_at': datetime.now().isoformat(),
                'service_version': '2.0'
            },
            'educational_value': {
                'learning_approach': 'visual_based',
                'engagement_level': 'high',
                'retention_potential': 'enhanced_through_visualization',
                'factual_accuracy': 'high'
            }
        }

    def _extract_file_content(self, file) -> str:
        """Extract text content from uploaded file."""
        try:
            from app.models.files import FilePage

            # Get file pages from database
            pages = db.session.query(FilePage).filter(
                FilePage.file_id == file.id
            ).order_by(FilePage.page_number).all()

            if not pages:
                logger.warning(f"No pages found for file {file.id}")
                return ""

            # Combine page text
            content = "\n\n".join([page.page_text or "" for page in pages if page.page_text])

            logger.info(f"Extracted {len(content)} characters from {len(pages)} pages")
            return content

        except Exception as e:
            logger.error(f"Error extracting file content: {str(e)}")
            return ""

    def _query_ai_service(self, prompt: str, max_tokens: int = 4000, temperature: float = 0.7) -> str:
        """
        Query the AI service with a prompt.

        Args:
            prompt: The prompt to send to the AI
            max_tokens: Maximum tokens in response
            temperature: Temperature for response generation

        Returns:
            AI response as string
        """
        try:
            messages = [
                {"role": "system", "content": "You are an expert at analyzing documents and identifying content that can be effectively visualized through diagrams, illustrations, and infographics. You focus on factual, literal representations of document content."},
                {"role": "user", "content": prompt}
            ]

            response = self._make_openai_call(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            return response

        except Exception as e:
            logger.error(f"Error querying AI service: {str(e)}")
            return f"Error generating content: {str(e)}"
