"""
AI Presentation Builder Service

Generates PowerPoint presentations from documents or topics using ChatGPT and DALL-E.
Two-stage process:
  Stage 1: Generate slide content with ChatGPT
  Stage 2: Generate images with DALL-E and create PPTX file
"""

import os
import logging
import json
import time
import requests
from typing import List, Dict, Any, Optional
from io import BytesIO
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from app.services.ai_service_base import AIServiceBase
from app.services.external.azure_image import azure_dalle_generate

logger = logging.getLogger(__name__)


# Theme Definitions (10 themes)
# Store RGB values as tuples for easy conversion
THEMES = {
    "professional_blue": {
        "name": "Professional Blue",
        "primary_color_rgb": (31, 78, 120),
        "secondary_color_rgb": (68, 114, 196),
        "accent_color_rgb": (255, 217, 102),
        "text_color_rgb": (0, 0, 0),
        "background_color_rgb": (255, 255, 255),
        "title_font": "Calibri",
        "body_font": "Calibri"
    },
    "creative_gradient": {
        "name": "Creative Gradient",
        "primary_color_rgb": (255, 87, 51),
        "secondary_color_rgb": (255, 195, 0),
        "accent_color_rgb": (76, 209, 55),
        "text_color_rgb": (51, 51, 51),
        "background_color_rgb": (255, 255, 255),
        "title_font": "Arial",
        "body_font": "Arial"
    },
    "minimalist_gray": {
        "name": "Minimalist Gray",
        "primary_color_rgb": (97, 97, 97),
        "secondary_color_rgb": (189, 189, 189),
        "accent_color_rgb": (0, 176, 240),
        "text_color_rgb": (64, 64, 64),
        "background_color_rgb": (250, 250, 250),
        "title_font": "Helvetica",
        "body_font": "Helvetica"
    },
    "academic_formal": {
        "name": "Academic Formal",
        "primary_color_rgb": (0, 32, 96),
        "secondary_color_rgb": (0, 102, 204),
        "accent_color_rgb": (204, 0, 0),
        "text_color_rgb": (0, 0, 0),
        "background_color_rgb": (255, 255, 255),
        "title_font": "Times New Roman",
        "body_font": "Times New Roman"
    },
    "dark_elegant": {
        "name": "Dark Elegant",
        "primary_color_rgb": (28, 28, 28),
        "secondary_color_rgb": (66, 66, 66),
        "accent_color_rgb": (255, 215, 0),
        "text_color_rgb": (255, 255, 255),
        "background_color_rgb": (28, 28, 28),
        "title_font": "Georgia",
        "body_font": "Georgia"
    },
    "nature_green": {
        "name": "Nature Green",
        "primary_color_rgb": (34, 139, 34),
        "secondary_color_rgb": (144, 238, 144),
        "accent_color_rgb": (255, 165, 0),
        "text_color_rgb": (0, 0, 0),
        "background_color_rgb": (245, 255, 245),
        "title_font": "Verdana",
        "body_font": "Verdana"
    },
    "tech_purple": {
        "name": "Tech Purple",
        "primary_color_rgb": (123, 31, 162),
        "secondary_color_rgb": (186, 104, 200),
        "accent_color_rgb": (0, 229, 255),
        "text_color_rgb": (33, 33, 33),
        "background_color_rgb": (255, 255, 255),
        "title_font": "Segoe UI",
        "body_font": "Segoe UI"
    },
    "warm_orange": {
        "name": "Warm Orange",
        "primary_color_rgb": (230, 81, 0),
        "secondary_color_rgb": (255, 152, 0),
        "accent_color_rgb": (255, 235, 59),
        "text_color_rgb": (51, 51, 51),
        "background_color_rgb": (255, 248, 240),
        "title_font": "Trebuchet MS",
        "body_font": "Trebuchet MS"
    },
    "ocean_blue": {
        "name": "Ocean Blue",
        "primary_color_rgb": (0, 105, 148),
        "secondary_color_rgb": (3, 169, 244),
        "accent_color_rgb": (0, 229, 255),
        "text_color_rgb": (0, 0, 0),
        "background_color_rgb": (240, 248, 255),
        "title_font": "Candara",
        "body_font": "Candara"
    },
    "corporate_red": {
        "name": "Corporate Red",
        "primary_color_rgb": (192, 0, 0),
        "secondary_color_rgb": (255, 87, 87),
        "accent_color_rgb": (255, 213, 79),
        "text_color_rgb": (0, 0, 0),
        "background_color_rgb": (255, 255, 255),
        "title_font": "Arial",
        "body_font": "Arial"
    }
}


class AIPresentationBuilderService(AIServiceBase):
    """Service for building AI-powered presentations with ChatGPT and DALL-E."""

    def __init__(self):
        super().__init__()
        self.service_name = "PresentationBuilder"
        self.model_name = "gpt-4"
        self.max_retries = 3
        self.rate_limit_delay = 15  # seconds between DALL-E requests

    def get_service_info(self) -> Dict[str, Any]:
        """
        Return information about this service.

        Returns:
            Dictionary with service information
        """
        return {
            'service_name': 'AIPresentationBuilder',
            'description': 'Creates professional PowerPoint presentations from documents or topics using ChatGPT and DALL-E',
            'capabilities': [
                'content_generation',
                'slide_structuring',
                'image_generation',
                'powerpoint_creation',
                'theme_customization'
            ],
            'supported_sources': ['file', 'vault', 'text'],
            'output_formats': ['pptx'],
            'themes_count': len(THEMES),
            'stages': {
                'stage_1': 'Generate slide content with ChatGPT',
                'stage_2': 'Generate images with DALL-E and create PowerPoint'
            }
        }

    def get_available_themes(self) -> List[Dict[str, Any]]:
        """
        Get list of available themes with metadata.

        Returns:
            List of theme dictionaries with name and color info
        """
        themes_list = []
        for theme_id, theme_data in THEMES.items():
            primary_rgb = theme_data['primary_color_rgb']
            secondary_rgb = theme_data['secondary_color_rgb']

            themes_list.append({
                'id': theme_id,
                'name': theme_data['name'],
                'primary_color': f"rgb({primary_rgb[0]}, {primary_rgb[1]}, {primary_rgb[2]})",
                'secondary_color': f"rgb({secondary_rgb[0]}, {secondary_rgb[1]}, {secondary_rgb[2]})"
            })
        return themes_list

    def _get_theme_colors(self, theme_id: str) -> Dict[str, RGBColor]:
        """
        Convert theme RGB tuples to RGBColor objects for PowerPoint.

        Args:
            theme_id: Theme identifier

        Returns:
            Dictionary with RGBColor objects
        """
        theme_data = THEMES.get(theme_id, THEMES["professional_blue"])
        return {
            'primary_color': RGBColor(*theme_data['primary_color_rgb']),
            'secondary_color': RGBColor(*theme_data['secondary_color_rgb']),
            'accent_color': RGBColor(*theme_data['accent_color_rgb']),
            'text_color': RGBColor(*theme_data['text_color_rgb']),
            'background_color': RGBColor(*theme_data['background_color_rgb']),
            'title_font': theme_data['title_font'],
            'body_font': theme_data['body_font']
        }

    def _query_ai_service(self, prompt: str, max_tokens: int = 4000, temperature: float = 0.7, response_format: dict = None) -> str:
        """
        Query the AI service with a prompt.

        Args:
            prompt: The prompt to send to the AI
            max_tokens: Maximum tokens in response
            temperature: Temperature for response generation
            response_format: Optional response format (e.g., {"type": "json_object"})

        Returns:
            AI response as string
        """
        try:
            messages = [
                {"role": "system", "content": "You are an expert presentation designer who creates engaging, well-structured slides with clear content and visual suggestions."},
                {"role": "user", "content": prompt}
            ]

            # Note: response_format is not supported by openai==0.28 ChatCompletion.create
            # We'll use _make_openai_call which doesn't support response_format
            # Instead, we'll instruct the model to return JSON in the prompt
            response = self._make_openai_call(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            return response

        except Exception as e:
            logger.error(f"Error querying AI service: {str(e)}")
            return f"Error generating content: {str(e)}"

    def _extract_content_from_file(self, file_obj) -> str:
        """
        Extract text content from uploaded file.

        Args:
            file_obj: UploadedFile database object

        Returns:
            Extracted text content
        """
        try:
            content_parts = []

            # Get all pages for this file
            pages = file_obj.pages if hasattr(file_obj, 'pages') else []

            for page in pages:
                if hasattr(page, 'page_text') and page.page_text:
                    content_parts.append(page.page_text)

            full_content = "\n\n".join(content_parts)

            if not full_content:
                logger.warning(f"No content extracted from file {file_obj.id}")
                return f"Document: {file_obj.original_file_name}"

            logger.info(f"Extracted {len(full_content)} characters from file {file_obj.id}")
            return full_content

        except Exception as e:
            logger.error(f"Error extracting content from file: {str(e)}")
            return f"Document: {file_obj.original_file_name}"

    def _create_content_summary(self, content: str, max_words: int = 500) -> str:
        """
        Create a summary of long content for ChatGPT processing.

        Args:
            content: Full content text
            max_words: Maximum words in summary

        Returns:
            Summarized content
        """
        words = content.split()
        if len(words) <= max_words:
            return content

        # Take beginning, middle, and end
        chunk_size = max_words // 3
        beginning = " ".join(words[:chunk_size])
        middle_start = len(words) // 2 - chunk_size // 2
        middle = " ".join(words[middle_start:middle_start + chunk_size])
        end = " ".join(words[-chunk_size:])

        summary = f"{beginning}\n\n[...middle section...]\n\n{middle}\n\n[...final section...]\n\n{end}"

        logger.info(f"Created summary: {len(content)} chars -> {len(summary)} chars")
        return summary

    # =============================================================================
    # PART 2: STAGE 1 - CONTENT GENERATION WITH CHATGPT
    # =============================================================================

    def generate_presentation_content(
        self,
        source_type: str,
        source_content: str,
        total_slides: int = 10,
        theme: str = "professional_blue",
        source_file=None
    ) -> Dict[str, Any]:
        """
        Stage 1: Generate presentation slide content using ChatGPT.

        Args:
            source_type: 'file', 'vault', or 'text'
            source_content: Topic or document content
            total_slides: Number of slides to generate (5-20)
            theme: Theme name
            source_file: Optional file object if source is file/vault

        Returns:
            Dictionary with presentation title and slides data
        """
        try:
            # Extract content from file if applicable
            if source_file:
                content = self._extract_content_from_file(source_file)
            else:
                content = source_content

            # Create summary if content is too long
            if len(content.split()) > 1000:
                content = self._create_content_summary(content, max_words=1000)

            # Generate slides with ChatGPT
            slides_data = self._generate_slides_with_chatgpt(content, total_slides, theme)

            # Extract presentation title
            title = slides_data[0].get('title', 'Presentation') if slides_data else 'Presentation'

            logger.info(f"Generated {len(slides_data)} slides for presentation: {title}")

            return {
                'success': True,
                'title': title,
                'slides': slides_data,
                'total_slides': len(slides_data),
                'metadata': {
                    'source_type': source_type,
                    'theme': theme,
                    'ai_model': self.model_name
                }
            }

        except Exception as e:
            logger.error(f"Error generating presentation content: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_slides_with_chatgpt(
        self,
        content: str,
        total_slides: int,
        theme: str
    ) -> List[Dict[str, Any]]:
        """
        Use ChatGPT to generate structured slide content.

        Args:
            content: Source content
            total_slides: Number of slides
            theme: Theme name

        Returns:
            List of slide dictionaries
        """
        prompt = f"""You are a professional presentation designer. Create a {total_slides}-slide presentation based on the following content.

Content:
{content}

CRITICAL REQUIREMENTS:
1. Create EXACTLY {total_slides} slides
2. SLIDE 1 MUST BE: Title slide with main title and subtitle
3. SLIDE 2 MUST BE: Summary/Overview slide with 5-7 key bullet points summarizing the entire document
4. SLIDES 3 to {total_slides-1}: Content slides with detailed information (5-8 bullets per slide with comprehensive details)
5. SLIDE {total_slides}: Conclusion slide

For each slide, provide:
   - slide_number (1 to {total_slides})
   - slide_type: "title", "summary", "content", "chart", or "conclusion"
   - title (max 60 characters)
   - subtitle (for title slide only)
   - content: array of 5-8 detailed bullet points (each max 150 characters) OR paragraph text
   - content_type: "bullets", "paragraph", or "chart"
   - chart_type: "bar", "line", or "pie" (only if content_type is "chart")
   - chart_data: {{labels: [...], values: [...]}} (only if chart_type specified)
   - notes: detailed speaker notes (2-3 sentences)
   - suggested_image: brief description of what image would be useful (optional)
   - image_prompt: detailed prompt for DALL-E image generation (optional)

IMPORTANT: Add MORE content to each slide. Users will edit after downloading. Better to have too much than too little.

Return ONLY a valid JSON array of slide objects. Example format:
[
  {{
    "slide_number": 1,
    "slide_type": "title",
    "title": "Main Presentation Title",
    "subtitle": "Brief Subtitle or Context",
    "content": [],
    "content_type": "bullets",
    "notes": "Opening slide - introduce the topic",
    "suggested_image": "Professional background image"
  }},
  {{
    "slide_number": 2,
    "slide_type": "summary",
    "title": "Overview / Executive Summary",
    "content": ["First key point of summary", "Second key point", "Third key point", "Fourth key point", "Fifth key point", "Sixth key point", "Seventh key point"],
    "content_type": "bullets",
    "notes": "This slide provides a comprehensive overview of the entire presentation",
    "suggested_image": "Overview concept illustration",
    "image_prompt": "Professional overview illustration with interconnected elements"
  }},
  {{
    "slide_number": 3,
    "slide_type": "content",
    "title": "Detailed Topic Area",
    "content": ["Detailed bullet point 1 with comprehensive information", "Detailed bullet point 2", "Detailed bullet point 3", "Detailed bullet point 4", "Detailed bullet point 5", "Detailed bullet point 6"],
    "content_type": "bullets",
    "notes": "Discuss each point in detail during presentation",
    "suggested_image": "Relevant visual for this topic"
  }}
]"""

        # Query ChatGPT with higher token limit for more content
        response = self._query_ai_service(
            prompt,
            max_tokens=3000,  # Increased for more detailed content
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        try:
            # Parse JSON response
            slides_data = json.loads(response)

            # Handle if response is wrapped in an object
            if isinstance(slides_data, dict) and 'slides' in slides_data:
                slides_data = slides_data['slides']

            # Ensure all slides have user_wants_image set to False initially
            for slide in slides_data:
                slide['user_wants_image'] = False
                slide['image_url'] = None
                slide['image_prompt'] = slide.get('suggested_image', '')

            return slides_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ChatGPT response as JSON: {str(e)}")
            # Fallback: create basic slides
            return self._create_fallback_slides(total_slides, content)

    def _create_fallback_slides(self, total_slides: int, content: str) -> List[Dict[str, Any]]:
        """Create basic slides if ChatGPT fails."""
        slides = [
            {
                "slide_number": 1,
                "slide_type": "title",
                "title": "Presentation",
                "subtitle": "Generated from content",
                "content": [],
                "content_type": "bullets",
                "notes": "",
                "user_wants_image": False,
                "image_url": None,
                "image_prompt": ""
            }
        ]

        # Add content slides
        for i in range(2, total_slides):
            slides.append({
                "slide_number": i,
                "slide_type": "content",
                "title": f"Topic {i-1}",
                "content": ["Content point 1", "Content point 2", "Content point 3"],
                "content_type": "bullets",
                "notes": "",
                "user_wants_image": False,
                "image_url": None,
                "image_prompt": ""
            })

        # Add conclusion
        slides.append({
            "slide_number": total_slides,
            "slide_type": "conclusion",
            "title": "Conclusion",
            "content": ["Summary", "Thank you"],
            "content_type": "bullets",
            "notes": "",
            "user_wants_image": False,
            "image_url": None,
            "image_prompt": ""
        })

        return slides

    # =============================================================================
    # PART 3: STAGE 2 - IMAGE GENERATION AND PPTX CREATION
    # =============================================================================

    def generate_images_for_slides(
        self,
        slides_data: List[Dict[str, Any]],
        image_style: str = "professional"
    ) -> List[Dict[str, Any]]:
        """
        Stage 2: Generate DALL-E images for selected slides.

        Args:
            slides_data: List of slide dictionaries
            image_style: 'professional' or 'creative'

        Returns:
            Updated slides_data with image URLs
        """
        try:
            updated_slides = []

            for slide in slides_data:
                if slide.get('user_wants_image') and slide.get('image_prompt'):
                    logger.info(f"Generating image for slide {slide['slide_number']}")

                    # Create DALL-E prompt based on image style
                    dalle_prompt = self._create_dalle_prompt(
                        slide['image_prompt'],
                        slide.get('title', ''),
                        image_style
                    )

                    # Generate image
                    # Map image_style to DALL-E style (professional->vivid, creative->vivid)
                    dalle_style = "vivid"  # DALL-E only supports "vivid" or "natural"
                    image_url = self._generate_image_with_dalle(
                        dalle_prompt,
                        size="1792x1024",  # 16:9 landscape
                        style=dalle_style
                    )

                    if image_url:
                        slide['dalle_image_url'] = image_url
                        logger.info(f"Successfully generated image for slide {slide['slide_number']}")
                    else:
                        logger.warning(f"Failed to generate image for slide {slide['slide_number']}")

                    # Rate limiting
                    time.sleep(self.rate_limit_delay)

                updated_slides.append(slide)

            return updated_slides

        except Exception as e:
            logger.error(f"Error generating images: {str(e)}")
            return slides_data

    def _create_dalle_prompt(self, base_prompt: str, slide_title: str, style: str) -> str:
        """Create optimized DALL-E prompt."""
        if style == "professional":
            style_suffix = "professional, clean, business presentation style, high quality, modern design, corporate aesthetic"
        else:  # creative
            style_suffix = "creative, colorful, engaging, artistic illustration, vibrant, eye-catching design"

        return f"{base_prompt}. {style_suffix}. Suitable for presentation slide titled '{slide_title}'. 16:9 landscape format."

    def _generate_image_with_dalle(self, prompt: str, size: str = "1792x1024", style: str = "vivid") -> Optional[str]:
        """
        Generate image with DALL-E using Azure.

        Args:
            prompt: Image generation prompt
            size: Image size (default "1792x1024" for 16:9)
            style: DALL-E style (vivid or natural)

        Returns:
            Image URL if successful, None otherwise
        """
        try:
            logger.info(f"Generating DALL-E image with prompt: {prompt[:100]}...")

            # Use the azure_dalle_generate function (same as story_to_comics)
            image_results = azure_dalle_generate(
                prompt=prompt,
                size=size,
                style=style,
                quality="hd",
                n=1
            )

            logger.info(f"DALL-E API response: {image_results}")

            if image_results and len(image_results) > 0 and image_results[0].get('url'):
                image_url = image_results[0]['url']
                logger.info(f"Successfully generated image: {image_url}")
                return image_url

            logger.warning("DALL-E returned no image URL")
            return None

        except Exception as e:
            logger.error(f"DALL-E image generation error: {str(e)}")
            return None

    def create_powerpoint(
        self,
        slides_data: List[Dict[str, Any]],
        theme: str = "professional_blue",
        title: str = "Presentation"
    ) -> bytes:
        """
        Create PowerPoint file from slides data.

        Args:
            slides_data: List of slide dictionaries
            theme: Theme name
            title: Presentation title

        Returns:
            PowerPoint file as bytes
        """
        try:
            prs = Presentation()
            prs.slide_width = Inches(10)  # 16:9 aspect ratio
            prs.slide_height = Inches(5.625)

            theme_config = self._get_theme_colors(theme)

            for slide_data in slides_data:
                self._add_slide_to_presentation(prs, slide_data, theme_config)

            # Save to BytesIO
            pptx_bytes = BytesIO()
            prs.save(pptx_bytes)
            pptx_bytes.seek(0)

            logger.info(f"Created PowerPoint with {len(slides_data)} slides")
            return pptx_bytes.getvalue()

        except Exception as e:
            logger.error(f"Error creating PowerPoint: {str(e)}")
            raise

    def _add_slide_to_presentation(
        self,
        prs: Presentation,
        slide_data: Dict[str, Any],
        theme_config: Dict[str, Any]
    ):
        """Add a single slide to the presentation."""
        slide_type = slide_data.get('slide_type', 'content')

        if slide_type == 'title':
            self._add_title_slide(prs, slide_data, theme_config)
        elif slide_data.get('azure_image_url'):
            # Slide has an image from Azure
            self._add_image_slide(prs, slide_data, theme_config)
        elif slide_data.get('chart_type'):
            self._add_chart_slide(prs, slide_data, theme_config)
        else:
            self._add_content_slide(prs, slide_data, theme_config)

    def _add_title_slide(self, prs, slide_data, theme_config):
        """Add title slide."""
        slide_layout = prs.slide_layouts[0]  # Title slide layout
        slide = prs.slides.add_slide(slide_layout)

        # Apply background color if theme has dark background
        self._apply_slide_background(slide, theme_config)

        # Set title
        title = slide.shapes.title
        title.text = slide_data.get('title', '')
        title.text_frame.paragraphs[0].font.size = Pt(44)
        title.text_frame.paragraphs[0].font.color.rgb = theme_config['primary_color']
        title.text_frame.paragraphs[0].font.bold = True

        # Set subtitle if available
        if len(slide.placeholders) > 1:
            subtitle = slide.placeholders[1]
            subtitle.text = slide_data.get('subtitle', '')
            subtitle.text_frame.paragraphs[0].font.size = Pt(28)
            subtitle.text_frame.paragraphs[0].font.color.rgb = theme_config['secondary_color']

    def _apply_slide_background(self, slide, theme_config):
        """Apply background color to slide based on theme."""
        try:
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = theme_config['background_color']
        except Exception as e:
            logger.warning(f"Could not apply background color: {str(e)}")

    def _add_content_slide(self, prs, slide_data, theme_config):
        """Add content slide with bullet points."""
        slide_layout = prs.slide_layouts[1]  # Title and content layout
        slide = prs.slides.add_slide(slide_layout)

        # Apply background color
        self._apply_slide_background(slide, theme_config)

        # Title
        title = slide.shapes.title
        title.text = slide_data.get('title', '')
        title.text_frame.paragraphs[0].font.size = Pt(32)
        title.text_frame.paragraphs[0].font.color.rgb = theme_config['primary_color']
        title.text_frame.paragraphs[0].font.bold = True

        # Content
        if len(slide.placeholders) > 1:
            body = slide.placeholders[1]
            tf = body.text_frame
            tf.clear()

            content = slide_data.get('content', [])
            for item in content:
                p = tf.add_paragraph()
                p.text = item
                p.font.size = Pt(18)
                p.font.color.rgb = theme_config['text_color']
                p.level = 0

    def _add_image_slide(self, prs, slide_data, theme_config):
        """Add slide with image."""
        slide_layout = prs.slide_layouts[6]  # Blank layout
        slide = prs.slides.add_slide(slide_layout)

        # Apply background color
        self._apply_slide_background(slide, theme_config)

        # Add title at top
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3),
            Inches(9), Inches(0.8)
        )
        title_frame = title_box.text_frame
        title_frame.text = slide_data.get('title', '')
        title_frame.paragraphs[0].font.size = Pt(32)
        title_frame.paragraphs[0].font.color.rgb = theme_config['primary_color']
        title_frame.paragraphs[0].font.bold = True

        # Download and add image from Azure URL
        azure_image_url = slide_data.get('azure_image_url')
        if azure_image_url:
            try:
                import requests
                logger.info(f"Downloading image from Azure for slide {slide_data.get('slide_number')}")

                # Download image
                response = requests.get(azure_image_url, timeout=30)
                response.raise_for_status()

                # Save to BytesIO
                image_stream = BytesIO(response.content)

                # Add image to slide (centered, below title)
                # Image area: from Y=1.2 inches to Y=5.0 inches (3.8 inch height)
                # X centered: 0.5 to 9.5 (9 inch width)
                left = Inches(0.5)
                top = Inches(1.3)
                width = Inches(9)
                height = Inches(3.8)

                slide.shapes.add_picture(image_stream, left, top, width=width, height=height)
                logger.info(f"Successfully added image to slide {slide_data.get('slide_number')}")

            except Exception as e:
                logger.error(f"Error adding image to slide: {str(e)}")
                # Add error message to slide if image fails
                error_box = slide.shapes.add_textbox(
                    Inches(2), Inches(2.5),
                    Inches(6), Inches(1)
                )
                error_box.text_frame.text = f"[Image failed to load: {str(e)[:50]}]"
                error_box.text_frame.paragraphs[0].font.size = Pt(14)
                error_box.text_frame.paragraphs[0].font.italic = True

    def _add_chart_slide(self, prs, slide_data, theme_config):
        """Add slide with chart - simplified version."""
        # For now, treat as content slide
        # Full chart implementation would require python-pptx chart features
        self._add_content_slide(prs, slide_data, theme_config)
