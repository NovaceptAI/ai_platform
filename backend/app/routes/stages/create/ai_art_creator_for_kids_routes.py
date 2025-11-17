"""
AI Art Creator for Kids API Routes

RESTful endpoints for kid-friendly AI art generation.
Supports creation, gallery browsing, favorites, and collections.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

from app.models.kid_art import KidArtCreation
from app.services.stages.create.ai_art_creator_for_kids_service import AIArtCreatorForKidsService
from app.services.kid_art_storage_service import save_kid_art_creation, delete_kid_art
from app.tasks.ai_art_creator_for_kids_task import generate_kid_art_task
from app.db import db

logger = logging.getLogger(__name__)

ai_art_creator_for_kids_bp = Blueprint(
    'ai_art_creator_for_kids',
    __name__,
    url_prefix='/api/stages/create/ai_art_creator_for_kids'
)

service = AIArtCreatorForKidsService()


# ==================== Service Info ====================

@ai_art_creator_for_kids_bp.route('/info', methods=['GET'])
@jwt_required()
def get_service_info():
    """Get service information and capabilities."""
    try:
        info = service.get_service_info()
        return jsonify({
            'success': True,
            'service_info': info
        }), 200

    except Exception as e:
        logger.error(f"Error getting service info: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== Templates & Guidance ====================

@ai_art_creator_for_kids_bp.route('/templates', methods=['GET'])
@jwt_required()
def get_creative_templates():
    """Get creative prompt templates."""
    try:
        templates = service.get_creative_prompts()
        return jsonify({
            'success': True,
            'templates': templates
        }), 200

    except Exception as e:
        logger.error(f"Error getting templates: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_art_creator_for_kids_bp.route('/styles', methods=['GET'])
@jwt_required()
def get_art_styles():
    """Get available art styles."""
    try:
        styles = service.get_art_styles()
        return jsonify({
            'success': True,
            'styles': styles
        }), 200

    except Exception as e:
        logger.error(f"Error getting styles: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_art_creator_for_kids_bp.route('/palettes', methods=['GET'])
@jwt_required()
def get_color_palettes():
    """Get available color palettes."""
    try:
        palettes = service.get_color_palettes()
        return jsonify({
            'success': True,
            'palettes': palettes
        }), 200

    except Exception as e:
        logger.error(f"Error getting palettes: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_art_creator_for_kids_bp.route('/magic-words', methods=['GET'])
@jwt_required()
def get_magic_words():
    """Get magic words suggestions."""
    try:
        magic_words = service.get_magic_words()
        return jsonify({
            'success': True,
            'magic_words': magic_words
        }), 200

    except Exception as e:
        logger.error(f"Error getting magic words: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== Art Generation ====================

@ai_art_creator_for_kids_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_kid_art():
    """
    Start kid art generation task.

    Request body:
    {
        "prompt_text": "A magical unicorn in a rainbow forest",
        "age_group": "8-10",
        "art_style": "cartoon",
        "color_palette": "rainbow",
        "num_variations": 2,
        "title": "My Magical Art",
        "story_text": "Once upon a time...",
        "character_name": "Sparkle",
        "collection_name": "My Animals"
    }

    Returns:
        Task ID for progress tracking
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # Validate required fields
        required_fields = ['prompt_text', 'age_group', 'art_style', 'color_palette']
        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Validate age group
        age_group = data['age_group']
        if age_group not in ['5-7', '8-10', '11-14']:
            return jsonify({
                'success': False,
                'error': 'Invalid age group. Must be 5-7, 8-10, or 11-14'
            }), 400

        # Validate num_variations
        num_variations = data.get('num_variations', 1)
        if not isinstance(num_variations, int) or num_variations < 1 or num_variations > 4:
            return jsonify({
                'success': False,
                'error': 'num_variations must be between 1 and 4'
            }), 400

        # Launch Celery task
        task = generate_kid_art_task.delay(user_id, data)

        logger.info(f"Started kid art generation task {task.id} for user {user_id}")

        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Art generation started! Check progress with the task_id.'
        }), 202

    except Exception as e:
        logger.error(f"Error starting kid art generation: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_art_creator_for_kids_bp.route('/progress/<task_id>', methods=['GET'])
@jwt_required()
def get_generation_progress(task_id):
    """Get progress of art generation task."""
    try:
        from celery.result import AsyncResult
        task = AsyncResult(task_id)

        if task.state == 'PENDING':
            response = {
                'success': True,
                'state': 'PENDING',
                'status': 'Waiting to start...',
                'progress': 0
            }
        elif task.state == 'PROGRESS':
            response = {
                'success': True,
                'state': 'PROGRESS',
                'status': task.info.get('status', ''),
                'progress': task.info.get('progress', 0),
                'current_step': task.info.get('current_step', 1),
                'total_steps': task.info.get('total_steps', 4)
            }
        elif task.state == 'SUCCESS':
            response = {
                'success': True,
                'state': 'SUCCESS',
                'status': 'Complete!',
                'progress': 100,
                'result': task.info
            }
        elif task.state == 'FAILURE':
            response = {
                'success': False,
                'state': 'FAILURE',
                'status': 'Failed',
                'error': str(task.info)
            }
        else:
            response = {
                'success': True,
                'state': task.state,
                'status': str(task.info),
                'progress': 0
            }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error getting task progress: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== Gallery & Artwork Management ====================

@ai_art_creator_for_kids_bp.route('/gallery', methods=['GET'])
@jwt_required()
def get_user_gallery():
    """
    Get user's artwork gallery.

    Query params:
        limit: Number of results (default 20)
        offset: Pagination offset (default 0)
        is_favorite: Filter by favorite status (optional)
        collection_name: Filter by collection (optional)
    """
    try:
        user_id = get_jwt_identity()

        # Parse query params
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        is_favorite = request.args.get('is_favorite', type=lambda v: v.lower() == 'true')
        collection_name = request.args.get('collection_name', None)

        # Validate limit
        if limit > 100:
            limit = 100

        # Get artworks
        artworks = KidArtCreation.get_user_artworks(
            user_id=user_id,
            limit=limit,
            offset=offset,
            is_favorite=is_favorite,
            collection_name=collection_name
        )

        # Get total count
        total_count = KidArtCreation.get_user_artworks_count(
            user_id=user_id,
            is_favorite=is_favorite,
            collection_name=collection_name
        )

        # Convert to dict
        artworks_data = [art.to_dict(include_images=False) for art in artworks]

        # Add thumbnail URLs
        for i, art in enumerate(artworks):
            if art.images and len(art.images) > 0:
                artworks_data[i]['thumbnail_url'] = art.images[0].get('thumbnail_url')

        return jsonify({
            'success': True,
            'artworks': artworks_data,
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        logger.error(f"Error getting gallery: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_art_creator_for_kids_bp.route('/collections', methods=['GET'])
@jwt_required()
def get_user_collections():
    """Get user's collection names."""
    try:
        user_id = get_jwt_identity()
        collections = KidArtCreation.get_user_collections(user_id)

        return jsonify({
            'success': True,
            'collections': collections
        }), 200

    except Exception as e:
        logger.error(f"Error getting collections: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_art_creator_for_kids_bp.route('/art/<art_id>', methods=['GET'])
@jwt_required()
def get_artwork_details(art_id):
    """Get detailed information about specific artwork."""
    try:
        user_id = get_jwt_identity()

        artwork = KidArtCreation.query.filter_by(
            id=art_id,
            user_id=user_id,
            status='active'
        ).first()

        if not artwork:
            return jsonify({
                'success': False,
                'error': 'Artwork not found'
            }), 404

        return jsonify({
            'success': True,
            'artwork': artwork.to_dict(include_images=True)
        }), 200

    except Exception as e:
        logger.error(f"Error getting artwork details: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_art_creator_for_kids_bp.route('/art/<art_id>', methods=['PUT'])
@jwt_required()
def update_artwork(art_id):
    """
    Update artwork metadata.

    Request body:
    {
        "title": "New Title",
        "story_text": "Updated story...",
        "is_favorite": true,
        "collection_name": "My Collection"
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        artwork = KidArtCreation.query.filter_by(
            id=art_id,
            user_id=user_id,
            status='active'
        ).first()

        if not artwork:
            return jsonify({
                'success': False,
                'error': 'Artwork not found'
            }), 404

        # Update allowed fields
        if 'title' in data:
            artwork.title = data['title']
        if 'story_text' in data:
            artwork.story_text = data['story_text']
        if 'is_favorite' in data:
            artwork.is_favorite = data['is_favorite']
        if 'collection_name' in data:
            artwork.collection_name = data['collection_name']
        if 'character_name' in data:
            artwork.character_name = data['character_name']

        db.session.commit()

        logger.info(f"Updated artwork {art_id} for user {user_id}")

        return jsonify({
            'success': True,
            'artwork': artwork.to_dict(include_images=True)
        }), 200

    except Exception as e:
        logger.error(f"Error updating artwork: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_art_creator_for_kids_bp.route('/art/<art_id>', methods=['DELETE'])
@jwt_required()
def delete_artwork(art_id):
    """Delete artwork (archives it and removes from Azure)."""
    try:
        user_id = get_jwt_identity()

        result = delete_kid_art(user_id, art_id)

        if result['success']:
            logger.info(f"Deleted artwork {art_id} for user {user_id}")
            return jsonify({
                'success': True,
                'message': 'Artwork deleted successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to delete artwork')
            }), 400

    except Exception as e:
        logger.error(f"Error deleting artwork: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== Prompt Validation ====================

@ai_art_creator_for_kids_bp.route('/validate-prompt', methods=['POST'])
@jwt_required()
def validate_prompt():
    """
    Validate and sanitize a kid's prompt before generation.

    Request body:
    {
        "prompt_text": "A magical dragon",
        "age_group": "8-10"
    }
    """
    try:
        data = request.get_json()

        prompt_text = data.get('prompt_text', '').strip()
        age_group = data.get('age_group', '8-10')

        if not prompt_text:
            return jsonify({
                'success': False,
                'error': 'prompt_text is required'
            }), 400

        # Sanitize prompt
        sanitization = service.sanitize_kid_prompt(prompt_text, age_group)

        return jsonify({
            'success': True,
            'sanitization': sanitization
        }), 200

    except Exception as e:
        logger.error(f"Error validating prompt: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
