"""
AI Art Creator for Kids Celery Tasks

Background tasks for kid-friendly AI art generation.
Handles async generation with progress tracking and safety checks.
"""

import logging
from typing import Dict, Any
from celery import current_app

from app.services.stages.create.ai_art_creator_for_kids_service import AIArtCreatorForKidsService
from app.services.kid_art_storage_service import save_kid_art_creation

logger = logging.getLogger(__name__)


@current_app.task(bind=True, name='tasks.generate_kid_art')
def generate_kid_art_task(self, user_id: str, art_data: Dict[str, Any]):
    """
    Generate kid-friendly AI artwork with progress tracking.

    Args:
        user_id: User ID
        art_data: Dict with prompt_text, age_group, art_style, color_palette, etc.

    Returns:
        Dict with success status and artwork details
    """
    try:
        service = AIArtCreatorForKidsService()

        # Extract parameters
        prompt_text = art_data.get('prompt_text')
        age_group = art_data.get('age_group')
        art_style = art_data.get('art_style')
        color_palette = art_data.get('color_palette')
        num_variations = art_data.get('num_variations', 1)
        title = art_data.get('title', 'My Artwork')
        story_text = art_data.get('story_text')
        character_name = art_data.get('character_name')
        collection_name = art_data.get('collection_name')

        logger.info(f"Starting kid art generation for user {user_id}")

        # Step 1: Sanitize prompt (10%)
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'Checking your idea is safe and fun...',
                'progress': 10,
                'current_step': 1,
                'total_steps': 4
            }
        )

        sanitization = service.sanitize_kid_prompt(prompt_text, age_group)

        if not sanitization['is_safe']:
            logger.warning(f"Unsafe prompt detected for user {user_id}")
            return {
                'success': False,
                'error': 'Content safety check failed',
                'warnings': sanitization['warnings']
            }

        # Step 2: Enhance prompt (20%)
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'Making your idea extra magical...',
                'progress': 20,
                'current_step': 2,
                'total_steps': 4
            }
        )

        enhanced_prompt = service.enhance_prompt_for_kids(
            prompt=sanitization['sanitized_prompt'],
            art_style=art_style,
            color_palette=color_palette,
            age_group=age_group
        )

        logger.info(f"Enhanced prompt for kid art: {enhanced_prompt[:100]}...")

        # Step 3: Generate images with DALL-E (30-70%)
        self.update_state(
            state='PROGRESS',
            meta={
                'status': f'Creating {num_variations} magical artwork{"s" if num_variations > 1 else ""}...',
                'progress': 30,
                'current_step': 3,
                'total_steps': 4
            }
        )

        generation_result = service.generate_kid_art(
            prompt_text=sanitization['sanitized_prompt'],
            age_group=age_group,
            art_style=art_style,
            color_palette=color_palette,
            num_variations=num_variations,
            size="1024x1024"
        )

        if not generation_result['success']:
            logger.error(f"Kid art generation failed: {generation_result.get('error')}")
            return {
                'success': False,
                'error': generation_result.get('error', 'Failed to generate artwork')
            }

        generated_images = generation_result['images']
        logger.info(f"Generated {len(generated_images)} kid art variations")

        # Step 4: Save to Azure and database (70-100%)
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'Saving your beautiful artwork...',
                'progress': 70,
                'current_step': 4,
                'total_steps': 4
            }
        )

        # Prepare metadata for storage
        storage_data = {
            'title': title,
            'prompt_text': prompt_text,
            'age_group': age_group,
            'art_style': art_style,
            'color_palette': color_palette,
            'story_text': story_text,
            'character_name': character_name,
            'collection_name': collection_name,
            'original_prompt': prompt_text,
            'sanitized_prompt': sanitization['sanitized_prompt'],
            'generation_metadata': {
                'enhanced_prompt': enhanced_prompt,
                'sanitization_flags': sanitization.get('flags', []),
                'dalle_size': '1024x1024',
                'dalle_style': 'vivid',
                'service_version': '1.0'
            }
        }

        # Save to Azure and database
        save_result = save_kid_art_creation(
            user_id=user_id,
            art_data=storage_data,
            images_with_dalle_urls=generated_images
        )

        if not save_result['success']:
            logger.error(f"Failed to save kid art: {save_result.get('error')}")
            return {
                'success': False,
                'error': save_result.get('error', 'Failed to save artwork')
            }

        logger.info(f"Successfully created kid art {save_result['art_id']} for user {user_id}")

        # Complete!
        return {
            'success': True,
            'art_id': save_result['art_id'],
            'num_variations': save_result['num_variations'],
            'images': save_result['images'],
            'title': title,
            'message': 'Your magical artwork is ready!'
        }

    except Exception as e:
        logger.error(f"Error in kid art generation task: {str(e)}", exc_info=True)
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'status': 'Something went wrong! Please try again.'
            }
        )
        return {
            'success': False,
            'error': str(e)
        }
