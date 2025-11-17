"""
Story to Comics Converter Service for Create Stage Learning Path.

This service transforms stories (from files, text, or vault) into comic strip panels
with AI-generated images for each panel.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.services.ai_service_base import AIServiceBase
from app.db import db
from app.services.external.azure_image import azure_dalle_generate

logger = logging.getLogger(__name__)


class StoryToComicsConverterService(AIServiceBase):
    """Service for converting stories into comic strip format with generated images."""

    def __init__(self):
        super().__init__()
        self.service_name = "StoryToComicsConverter"

    def get_service_info(self) -> Dict[str, Any]:
        """
        Return information about this service.

        Returns:
            Dictionary with service information
        """
        return {
            'service_name': 'StoryToComicsConverter',
            'description': 'Converts stories into comic strip format with AI-generated panel images',
            'capabilities': [
                'story_analysis',
                'comic_panel_creation',
                'dialogue_extraction',
                'scene_visualization',
                'character_identification'
            ],
            'supported_styles': ['vivid', 'natural'],
            'max_panels_per_comic': 12,
            'version': '1.0'
        }

    def convert_story_to_comic(self, source_type: str, source_content: str,
                               num_panels: int = 6, style: str = "vivid",
                               source_file=None) -> Dict[str, Any]:
        """
        Convert a story into comic strip format.

        Args:
            source_type: Type of source ('file', 'text', 'vault')
            source_content: The story content (text or file content)
            num_panels: Number of comic panels to generate (max 12)
            style: Image style - "vivid" or "natural"
            source_file: Optional file object if source_type is 'file' or 'vault'

        Returns:
            Dictionary containing comic strip data
        """
        try:
            logger.info(f"Converting story to comic: source_type={source_type}, num_panels={num_panels}")

            # Limit panels to maximum
            num_panels = min(num_panels, 12)

            # Extract content based on source type
            if source_type in ['file', 'vault'] and source_file:
                content = self._extract_file_content(source_file)
                source_name = source_file.original_file_name
            else:  # text
                content = source_content
                source_name = "User Story"

            if not content:
                raise ValueError("No content provided for comic conversion")

            # Analyze story for comic conversion
            story_analysis = self._analyze_story_for_comics(content)

            # Create comic panels structure
            comic_panels = self._create_comic_panels(content, story_analysis, num_panels)

            # Generate metadata
            metadata = self._create_comic_metadata(source_type, source_name, num_panels, style)

            logger.info(f"Successfully analyzed story and created {len(comic_panels)} panel structures")

            return {
                'comic_data': {
                    'title': story_analysis.get('title', 'Comic Story'),
                    'panels': comic_panels,
                    'total_panels': len(comic_panels),
                    'creation_date': datetime.now().strftime("%B %d, %Y")
                },
                'metadata': metadata,
                'story_analysis': story_analysis
            }

        except Exception as e:
            logger.error(f"Error converting story to comic: {str(e)}")
            raise

    def generate_comic_images(self, comic_data: Dict[str, Any], style: str = "vivid",
                             size: str = "1792x1024") -> List[Dict[str, Any]]:
        """
        Generate images for comic panels using DALL-E.

        Args:
            comic_data: The comic data dictionary with panels
            style: Image style - "vivid" or "natural"
            size: Image size - "1792x1024" (landscape for comic panels)

        Returns:
            List of panels with generated images
        """
        try:
            panels = comic_data.get('panels', [])
            logger.info(f"Generating images for {len(panels)} comic panels")

            generated_panels = []

            for i, panel in enumerate(panels, 1):
                try:
                    logger.info(f"Generating image for panel {i}/{len(panels)}: {panel.get('title')}")

                    # Create comic-specific image prompt
                    image_prompt = self._create_comic_panel_prompt(panel, style)

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

                    logger.info(f"DALL-E API response for panel {i}: {image_results}")

                    if image_results and len(image_results) > 0 and image_results[0].get('url'):
                        image_url = image_results[0]['url']

                        generated_panels.append({
                            'panel_number': i,
                            'title': panel.get('title', f'Panel {i}'),
                            'scene_description': panel.get('scene_description', ''),
                            'dialogue': panel.get('dialogue', []),
                            'narration': panel.get('narration', ''),
                            'image_url': image_url,
                            'image_prompt': image_prompt,
                            'revised_prompt': image_results[0].get('revised_prompt'),
                            'style': style,
                            'size': size
                        })

                        logger.info(f" Successfully generated image for panel {i}")
                    else:
                        logger.warning(f"No image URL returned for panel {i}")
                        generated_panels.append({
                            'panel_number': i,
                            'title': panel.get('title', f'Panel {i}'),
                            'scene_description': panel.get('scene_description', ''),
                            'dialogue': panel.get('dialogue', []),
                            'narration': panel.get('narration', ''),
                            'error': 'No image generated',
                            'image_prompt': image_prompt
                        })

                except Exception as e:
                    logger.error(f"Error generating image for panel {i}: {str(e)}")
                    generated_panels.append({
                        'panel_number': i,
                        'title': panel.get('title', f'Panel {i}'),
                        'scene_description': panel.get('scene_description', ''),
                        'error': str(e)
                    })
                    continue

            logger.info(f"Completed comic image generation: {len([p for p in generated_panels if 'image_url' in p])}/{len(generated_panels)} successful")

            return generated_panels

        except Exception as e:
            logger.error(f"Error in comic image generation: {str(e)}")
            raise

    def _analyze_story_for_comics(self, content: str) -> Dict[str, Any]:
        """Analyze story content to identify comic-suitable elements."""

        prompt = f"""
        Analyze this story for conversion into a comic strip format.

        Story content:
        {content[:3000]}

        Identify:
        1. Main characters (names, descriptions, key traits)
        2. Key scenes or moments that would make good comic panels
        3. Important dialogue or quotes
        4. The story's tone and mood
        5. Suggested comic title

        Provide a structured analysis suitable for comic creation.
        """

        analysis_response = self._query_ai_service(prompt, max_tokens=700, temperature=0.4)

        return {
            'content_analysis': analysis_response,
            'title': self._extract_title_from_analysis(analysis_response, content),
            'comic_suitable': True
        }

    def _extract_title_from_analysis(self, analysis: str, content: str) -> str:
        """Extract or generate a title from the analysis."""
        # Simple extraction - look for "title" in analysis
        lines = analysis.lower().split('\n')
        for line in lines:
            if 'title:' in line:
                return line.split('title:')[1].strip().strip('"').strip("'")

        # If no title found, generate one from first few words
        words = content.split()[:5]
        return ' '.join(words) + "..." if len(content.split()) > 5 else ' '.join(words)

    def _create_comic_panels(self, content: str, story_analysis: Dict[str, Any],
                            num_panels: int) -> List[Dict[str, Any]]:
        """Create structured comic panels from the story."""

        prompt = f"""
        Convert this story into {num_panels} comic strip panels.

        Story:
        {content[:4000]}

        For each panel, provide:
        1. Panel Title (brief, 2-4 words)
        2. Scene Description (visual description for image generation, 50-100 words)
        3. Dialogue (character speeches in format "Character: dialogue")
        4. Narration (optional narrative text boxes)

        Create {num_panels} panels that tell the story sequentially.
        Make visual descriptions vivid and specific for comic-style illustration.

        Format each panel as:
        Panel X:
        Title: [panel title]
        Scene: [detailed visual description]
        Dialogue: [character: speech] OR [none]
        Narration: [narrative text] OR [none]
        """

        panels_response = self._query_ai_service(prompt, max_tokens=2000, temperature=0.5)

        # Parse the response into structured panels
        panels = self._parse_comic_panels_response(panels_response, num_panels)

        return panels

    def _parse_comic_panels_response(self, panels_response: str, num_panels: int) -> List[Dict[str, Any]]:
        """Parse AI response into structured comic panel dictionaries."""
        panels_list = []

        # Split response into individual panels
        panel_blocks = panels_response.split('Panel ')

        for block in panel_blocks:
            if not block.strip() or block.strip().startswith('X'):
                continue

            try:
                # Extract panel data
                lines = block.strip().split('\n')
                panel_data = {
                    'title': 'Comic Panel',
                    'scene_description': '',
                    'dialogue': [],
                    'narration': ''
                }

                current_field = None
                for line in lines:
                    line = line.strip()

                    if line.startswith('Title:'):
                        panel_data['title'] = line.replace('Title:', '').strip()
                        current_field = None
                    elif line.startswith('Scene:'):
                        panel_data['scene_description'] = line.replace('Scene:', '').strip()
                        current_field = 'scene'
                    elif line.startswith('Dialogue:'):
                        dialogue_text = line.replace('Dialogue:', '').strip()
                        if dialogue_text.lower() != 'none' and dialogue_text:
                            # Parse dialogue format "Character: speech"
                            if ':' in dialogue_text:
                                panel_data['dialogue'].append(dialogue_text)
                        current_field = 'dialogue'
                    elif line.startswith('Narration:'):
                        narration_text = line.replace('Narration:', '').strip()
                        if narration_text.lower() != 'none':
                            panel_data['narration'] = narration_text
                        current_field = None
                    elif line and current_field == 'scene':
                        # Continue scene description
                        panel_data['scene_description'] += ' ' + line
                    elif line and current_field == 'dialogue' and line.lower() != 'none':
                        # Continue dialogue
                        if ':' in line:
                            panel_data['dialogue'].append(line)

                # Only add if we have meaningful content
                if panel_data['scene_description']:
                    panels_list.append(panel_data)

            except Exception as e:
                logger.warning(f"Error parsing panel block: {str(e)}")
                continue

        # If parsing failed or not enough panels, create default panels
        if len(panels_list) < num_panels:
            logger.warning(f"Only parsed {len(panels_list)} panels, creating defaults")
            for i in range(len(panels_list), num_panels):
                panels_list.append({
                    'title': f'Panel {i+1}',
                    'scene_description': 'Comic panel scene',
                    'dialogue': [],
                    'narration': ''
                })

        return panels_list[:num_panels]

    def _create_comic_panel_prompt(self, panel: Dict[str, Any], style: str) -> str:
        """Create a DALL-E prompt for a comic panel."""

        scene = panel.get('scene_description', '')
        title = panel.get('title', 'Comic Panel')

        # Create comic-specific prompt
        prompt_request = f"""
        Create a detailed description for generating a comic book panel illustration:

        Panel: {title}
        Scene: {scene}

        Generate a description (max 200 words) for a comic book style illustration that shows:
        - The scene described above in comic book art style
        - Clear character expressions and actions
        - Dynamic composition suitable for a comic panel
        - Visual storytelling elements
        - Comic book/graphic novel aesthetic

        Focus on creating a single, clear comic panel illustration.
        """

        # Get AI to refine the image prompt
        image_description = self._query_ai_service(prompt_request, max_tokens=250, temperature=0.5)

        # Clean up and format
        image_prompt = image_description.strip()

        # Add style guidance
        if style == "vivid":
            image_prompt += ". Bold comic book style with vibrant colors, dynamic action, clear character designs, comic panel illustration."
        else:
            image_prompt += ". Realistic comic book style with natural colors, detailed linework, graphic novel aesthetic."

        logger.info(f"Created comic panel prompt: {image_prompt[:100]}...")

        return image_prompt

    def _create_comic_metadata(self, source_type: str, source_name: str,
                              num_panels: int, style: str) -> Dict[str, Any]:
        """Create metadata for the comic creation."""

        return {
            'source_info': {
                'source_type': source_type,
                'source_name': source_name,
                'conversion_type': 'story_to_comic'
            },
            'comic_config': {
                'num_panels': num_panels,
                'style': style,
                'generated_at': datetime.now().isoformat(),
                'service_version': '1.0'
            },
            'format': {
                'type': 'comic_strip',
                'panel_layout': 'sequential',
                'includes_dialogue': True,
                'includes_narration': True
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
                {"role": "system", "content": "You are an expert at analyzing stories and converting them into comic book format. You understand visual storytelling, panel composition, and comic narrative structure."},
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
