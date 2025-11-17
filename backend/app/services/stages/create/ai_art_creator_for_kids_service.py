"""
AI Art Creator for Kids Service

Educational AI art generation service designed for children.
Includes safety filters, age-appropriate prompts, and creative guidance.
"""

import logging
import re
from typing import Dict, Any, List, Optional
from app.services.ai_service_base import AIServiceBase
from app.services.external.azure_image import azure_dalle_generate

logger = logging.getLogger(__name__)


class AIArtCreatorForKidsService(AIServiceBase):
    """Service for creating kid-friendly AI artwork with educational features."""

    def __init__(self):
        super().__init__()
        self.service_name = "AIArtCreatorForKids"
        self.model_name = "dall-e-3"
        self.max_retries = 3

    def get_service_info(self) -> Dict[str, Any]:
        """Return service metadata."""
        return {
            'service_name': 'AIArtCreatorForKids',
            'description': 'Create magical AI artwork designed for children with safety filters and creative guidance',
            'capabilities': [
                'kid_friendly_prompts',
                'safety_filtering',
                'art_style_options',
                'multiple_variations',
                'creative_templates',
                'age_appropriate_content'
            ],
            'age_groups': ['5-7', '8-10', '11-14'],
            'max_variations': 4,
            'supported_styles': self.get_art_styles(),
            'supported_palettes': self.get_color_palettes()
        }

    # ==================== Safety & Sanitization ====================

    def sanitize_kid_prompt(self, prompt: str, age_group: str) -> Dict[str, Any]:
        """
        Sanitize and validate kid's prompt for safety.

        Args:
            prompt: Raw prompt from kid
            age_group: Age group (5-7, 8-10, 11-14)

        Returns:
            Dict with {is_safe, sanitized_prompt, flags, warnings}
        """
        try:
            original_prompt = prompt.strip()
            sanitized = original_prompt.lower()
            flags = []
            warnings = []

            # Blocked words (violence, scary, inappropriate)
            blocked_words = [
                'blood', 'gore', 'kill', 'death', 'weapon', 'gun', 'knife',
                'scary', 'horror', 'evil', 'demon', 'monster', 'zombie',
                'nude', 'naked', 'sexy', 'adult',
                'drug', 'alcohol', 'cigarette', 'smoke'
            ]

            # Celebrity/person detection (simplified)
            person_indicators = ['person', 'celebrity', 'famous', 'real person']

            # Check for blocked content
            for word in blocked_words:
                if word in sanitized:
                    flags.append(f"inappropriate_content:{word}")
                    warnings.append(f"We can't create images with '{word}'. Let's make something fun and friendly instead!")

            # Check for people/celebrities (Azure DALL-E restriction)
            for indicator in person_indicators:
                if indicator in sanitized:
                    flags.append("person_detected")
                    warnings.append("Let's create imaginary characters instead of real people!")

            # Replace concerning words with kid-friendly alternatives
            replacements = {
                'fight': 'play',
                'battle': 'adventure',
                'scary': 'exciting',
                'monster': 'friendly creature',
                'alien': 'space friend'
            }

            for old, new in replacements.items():
                if old in sanitized:
                    sanitized = sanitized.replace(old, new)
                    flags.append(f"word_replaced:{old}->{new}")

            # Remove potential celebrity names (basic pattern matching)
            # This is a simplified approach - full implementation would use NER
            words = sanitized.split()
            capitalized_words = [w for w in original_prompt.split() if w and w[0].isupper() and len(w) > 2]
            if len(capitalized_words) > 2:
                # Likely contains proper nouns/names
                flags.append("possible_person_name")
                warnings.append("Let's create original characters with made-up names!")

            # Age-specific guidance
            if age_group == "5-7":
                # Younger kids: simpler, more colorful
                if len(sanitized.split()) > 15:
                    warnings.append("Great imagination! Let's keep it simple with a few fun words.")

            is_safe = len([f for f in flags if f.startswith('inappropriate_')]) == 0

            return {
                'is_safe': is_safe,
                'original_prompt': original_prompt,
                'sanitized_prompt': sanitized if is_safe else "",
                'flags': flags,
                'warnings': warnings
            }

        except Exception as e:
            logger.error(f"Error sanitizing kid prompt: {str(e)}")
            return {
                'is_safe': False,
                'original_prompt': prompt,
                'sanitized_prompt': "",
                'flags': ['error'],
                'warnings': ['Something went wrong. Please try describing your idea in a different way!']
            }

    def enhance_prompt_for_kids(
        self,
        prompt: str,
        art_style: str,
        color_palette: str,
        age_group: str
    ) -> str:
        """
        Enhance kid's prompt with artistic details for DALL-E.

        Args:
            prompt: Sanitized kid prompt
            art_style: Art style (cartoon, watercolor, etc.)
            color_palette: Color palette
            age_group: Age group

        Returns:
            Enhanced DALL-E prompt
        """
        try:
            # Get style descriptions
            styles = {style['id']: style for style in self.get_art_styles()}
            style_desc = styles.get(art_style, {}).get('dalle_keywords', 'colorful illustration')

            # Get palette descriptions
            palettes = {pal['id']: pal for pal in self.get_color_palettes()}
            palette_desc = palettes.get(color_palette, {}).get('description', 'vibrant colors')

            # Age-specific enhancements
            age_enhancements = {
                '5-7': 'simple, cheerful, bright, friendly, big eyes, cute',
                '8-10': 'detailed, imaginative, adventurous, creative',
                '11-14': 'detailed, expressive, dynamic, artistic'
            }

            age_keywords = age_enhancements.get(age_group, 'colorful, creative')

            # Build enhanced prompt
            enhanced_parts = [
                prompt,
                style_desc,
                palette_desc,
                age_keywords,
                'child-friendly',
                'educational illustration',
                'safe for kids',
                'wholesome content'
            ]

            enhanced_prompt = ', '.join(enhanced_parts)

            # Ensure kid-safe keywords
            enhanced_prompt += ', no text, no words, no people, no violence, appropriate for children'

            logger.info(f"Enhanced kid prompt: {enhanced_prompt[:100]}...")
            return enhanced_prompt

        except Exception as e:
            logger.error(f"Error enhancing kid prompt: {str(e)}")
            # Fallback to basic safe prompt
            return f"{prompt}, colorful children's illustration, kid-friendly, safe for all ages"

    # ==================== Art Generation ====================

    def generate_kid_art(
        self,
        prompt_text: str,
        age_group: str,
        art_style: str,
        color_palette: str,
        num_variations: int = 1,
        size: str = "1024x1024"
    ) -> Dict[str, Any]:
        """
        Generate kid-friendly artwork using DALL-E.

        Args:
            prompt_text: Kid's description
            age_group: Age group
            art_style: Art style ID
            color_palette: Color palette ID
            num_variations: Number of variations (1-4)
            size: Image size

        Returns:
            Dict with {success, images, error}
        """
        try:
            # Step 1: Sanitize prompt
            sanitization = self.sanitize_kid_prompt(prompt_text, age_group)

            if not sanitization['is_safe']:
                return {
                    'success': False,
                    'error': 'Content safety check failed',
                    'warnings': sanitization['warnings'],
                    'images': []
                }

            # Step 2: Enhance prompt
            enhanced_prompt = self.enhance_prompt_for_kids(
                prompt=sanitization['sanitized_prompt'],
                art_style=art_style,
                color_palette=color_palette,
                age_group=age_group
            )

            # Step 3: Generate with DALL-E
            generated_images = []

            for i in range(num_variations):
                try:
                    logger.info(f"Generating kid art variation {i+1}/{num_variations}")

                    # Call Azure DALL-E
                    image_results = azure_dalle_generate(
                        prompt=enhanced_prompt,
                        size=size,
                        style="vivid",  # More creative for kids
                        quality="standard",  # Standard quality is fine for kids
                        n=1
                    )

                    if image_results and len(image_results) > 0:
                        dalle_url = image_results[0].get('url')
                        if dalle_url:
                            generated_images.append({
                                'variation_num': i + 1,
                                'dalle_url': dalle_url
                            })
                            logger.info(f"Successfully generated variation {i+1}")
                        else:
                            logger.warning(f"No URL in DALL-E result for variation {i+1}")
                    else:
                        logger.warning(f"Empty result from DALL-E for variation {i+1}")

                except Exception as img_error:
                    logger.error(f"Error generating variation {i+1}: {str(img_error)}")
                    # Continue to next variation instead of failing completely

            if not generated_images:
                return {
                    'success': False,
                    'error': 'Failed to generate any images',
                    'images': []
                }

            return {
                'success': True,
                'images': generated_images,
                'sanitization': sanitization,
                'enhanced_prompt': enhanced_prompt,
                'num_generated': len(generated_images)
            }

        except Exception as e:
            logger.error(f"Error in kid art generation: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'images': []
            }

    # ==================== Creative Templates & Guidance ====================

    def get_creative_prompts(self) -> List[Dict[str, Any]]:
        """Get creative prompt templates for kids."""
        return [
            {
                'id': 'magical_animal',
                'title': 'Magical Animal',
                'icon': '🦄',
                'template': 'A magical [animal] with [special feature] in [setting]',
                'examples': [
                    'A magical unicorn with rainbow wings in a candy forest',
                    'A flying cat with sparkly tail in the clouds',
                    'A friendly dragon with flower scales in a garden'
                ]
            },
            {
                'id': 'dream_world',
                'title': 'Dream World',
                'icon': '🌈',
                'template': 'A beautiful [place] made of [material] with [elements]',
                'examples': [
                    'A castle made of ice cream with candy decorations',
                    'An island made of flowers with butterfly friends',
                    'A city made of books with rainbow bridges'
                ]
            },
            {
                'id': 'space_adventure',
                'title': 'Space Adventure',
                'icon': '🚀',
                'template': 'A space [thing] exploring [location] with [companions]',
                'examples': [
                    'A rocket ship exploring a planet made of crystals',
                    'An astronaut bunny discovering a moon garden',
                    'A space station floating near colorful nebulas'
                ]
            },
            {
                'id': 'underwater_fun',
                'title': 'Underwater Fun',
                'icon': '🐠',
                'template': 'An underwater [scene] with [creatures] and [features]',
                'examples': [
                    'A coral reef with friendly fish and treasure',
                    'A mermaid palace with dolphins and pearls',
                    'An ocean playground with sea turtles and bubbles'
                ]
            },
            {
                'id': 'nature_magic',
                'title': 'Nature Magic',
                'icon': '🌸',
                'template': 'A magical [nature] with [colors] and [animals]',
                'examples': [
                    'A rainbow forest with butterflies and fireflies',
                    'A flower meadow with bees and ladybugs',
                    'A waterfall garden with hummingbirds and frogs'
                ]
            },
            {
                'id': 'robot_friend',
                'title': 'Robot Friend',
                'icon': '🤖',
                'template': 'A friendly robot that [action] in [setting]',
                'examples': [
                    'A friendly robot that makes rainbows in a park',
                    'A helper robot that grows flowers in a garden',
                    'A music robot that plays songs with stars'
                ]
            }
        ]

    def get_art_styles(self) -> List[Dict[str, Any]]:
        """Get available art styles for kids."""
        return [
            {
                'id': 'cartoon',
                'name': 'Cartoon',
                'description': 'Fun and bouncy like your favorite cartoons!',
                'icon': '🎨',
                'dalle_keywords': 'cartoon style, animated, bold outlines, expressive',
                'preview_color': '#FF6B9D'
            },
            {
                'id': 'watercolor',
                'name': 'Watercolor',
                'description': 'Soft and dreamy like painting with water',
                'icon': '🖌️',
                'dalle_keywords': 'watercolor painting, soft edges, flowing colors',
                'preview_color': '#A8D8EA'
            },
            {
                'id': 'storybook',
                'name': 'Storybook',
                'description': 'Like pictures from your favorite books!',
                'icon': '📚',
                'dalle_keywords': 'children\'s book illustration, whimsical, detailed',
                'preview_color': '#FFD93D'
            },
            {
                'id': 'crayon',
                'name': 'Crayon Art',
                'description': 'Colorful like drawing with crayons',
                'icon': '🖍️',
                'dalle_keywords': 'crayon drawing style, textured, child art aesthetic',
                'preview_color': '#95E1D3'
            },
            {
                'id': 'digital',
                'name': 'Digital Art',
                'description': 'Bright and modern digital artwork',
                'icon': '💫',
                'dalle_keywords': 'digital illustration, vibrant, polished',
                'preview_color': '#C7CEEA'
            },
            {
                'id': 'pixel',
                'name': 'Pixel Art',
                'description': 'Fun blocky art like video games!',
                'icon': '🎮',
                'dalle_keywords': 'pixel art style, retro gaming aesthetic, colorful pixels',
                'preview_color': '#B4F8C8'
            }
        ]

    def get_color_palettes(self) -> List[Dict[str, Any]]:
        """Get available color palettes for kids."""
        return [
            {
                'id': 'rainbow',
                'name': 'Rainbow Magic',
                'description': 'All the colors of the rainbow!',
                'colors': ['#FF0000', '#FF7F00', '#FFFF00', '#00FF00', '#0000FF', '#4B0082', '#9400D3'],
                'description': 'bright rainbow colors, full spectrum, vibrant'
            },
            {
                'id': 'pastel',
                'name': 'Soft & Sweet',
                'description': 'Gentle pastel colors like candy',
                'colors': ['#FFD1DC', '#AEC6CF', '#FFFFBA', '#E0BBE4', '#FFDAB9'],
                'description': 'soft pastel colors, gentle tones, light and airy'
            },
            {
                'id': 'ocean',
                'name': 'Ocean Blues',
                'description': 'Cool blues and greens like the sea',
                'colors': ['#006994', '#0099CC', '#66CCCC', '#003366', '#336699'],
                'description': 'ocean blue and aqua colors, underwater palette'
            },
            {
                'id': 'sunset',
                'name': 'Sunset Glow',
                'description': 'Warm oranges and pinks like sunset',
                'colors': ['#FF6B6B', '#FFA500', '#FFD700', '#FF69B4', '#FF8C94'],
                'description': 'warm sunset colors, orange pink and gold tones'
            },
            {
                'id': 'forest',
                'name': 'Forest Green',
                'description': 'Greens and browns like nature',
                'colors': ['#228B22', '#90EE90', '#8B4513', '#32CD32', '#006400'],
                'description': 'natural green and brown tones, forest colors'
            },
            {
                'id': 'neon',
                'name': 'Neon Bright',
                'description': 'Super bright glowing colors!',
                'colors': ['#FF10F0', '#00FF00', '#00FFFF', '#FFFF00', '#FF0080'],
                'description': 'bright neon colors, glowing, electric vibrant'
            },
            {
                'id': 'galaxy',
                'name': 'Galaxy Space',
                'description': 'Purple and blue like outer space',
                'colors': ['#4B0082', '#9400D3', '#1E90FF', '#000080', '#8A2BE2'],
                'description': 'deep purple and blue galaxy colors, cosmic space tones'
            }
        ]

    def get_magic_words(self) -> Dict[str, List[str]]:
        """Get 'magic words' suggestions to enhance prompts."""
        return {
            'settings': [
                'magical forest', 'candy land', 'underwater world', 'cloud city',
                'flower garden', 'crystal cave', 'rainbow valley', 'star field',
                'enchanted castle', 'treasure island', 'bubble land', 'dream sky'
            ],
            'features': [
                'sparkling', 'glowing', 'shimmering', 'rainbow', 'colorful',
                'glittery', 'twinkling', 'bright', 'magical', 'fluffy',
                'shiny', 'transparent', 'holographic', 'golden', 'silver'
            ],
            'moods': [
                'happy', 'peaceful', 'exciting', 'cheerful', 'playful',
                'cozy', 'adventurous', 'dreamy', 'magical', 'joyful',
                'friendly', 'wonderful', 'amazing', 'fun', 'delightful'
            ],
            'companions': [
                'friendly animals', 'butterflies', 'birds', 'stars',
                'clouds', 'flowers', 'fireflies', 'bubbles', 'hearts',
                'dolphins', 'rabbits', 'kittens', 'puppies', 'fish'
            ]
        }
