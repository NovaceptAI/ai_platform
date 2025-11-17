"""
AI 3D Model Builder API Routes

RESTful endpoints for AI-powered 3D model generation.
Stage 1: Text-to-3D with simple geometry and basic rendering.
"""

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.status import Progress
from app.models.three_d_models import ThreeDModelCreation
from app.db import db
from app.tasks.ai_3d_model_builder_tasks import generate_3d_model_task
from app.services.three_d_model_storage_service import delete_3d_model
from app.services.stages.create.ai_3d_model_builder_service import AI3DModelBuilderService
import uuid
from datetime import datetime
import logging
import requests
from io import BytesIO

# Set up logging
log = logging.getLogger(__name__)

# Create Blueprint
ai_3d_model_builder_bp = Blueprint('ai_3d_model_builder', __name__)


# ==================== Service Info ====================

@ai_3d_model_builder_bp.route('/info', methods=['GET'])
@jwt_required()
def get_service_info():
    """Get service information and capabilities."""
    try:
        service = AI3DModelBuilderService()
        info = service.get_service_info()

        return jsonify({
            'success': True,
            'service_info': info
        }), 200

    except Exception as e:
        log.error(f"Error getting service info: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_3d_model_builder_bp.route('/styles', methods=['GET'])
def get_available_styles():
    """Get list of available 3D styles."""
    try:
        service = AI3DModelBuilderService()
        styles = service.get_available_styles()

        return jsonify({
            'success': True,
            'styles': styles
        }), 200

    except Exception as e:
        log.error(f"Error getting styles: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_3d_model_builder_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get suggested categories for 3D objects."""
    try:
        categories = [
            {'id': 'objects', 'name': 'Objects', 'icon': '🎁', 'examples': ['cup', 'chair', 'lamp']},
            {'id': 'vehicles', 'name': 'Vehicles', 'icon': '🚗', 'examples': ['car', 'airplane', 'boat']},
            {'id': 'buildings', 'name': 'Buildings', 'icon': '🏛️', 'examples': ['house', 'castle', 'tower']},
            {'id': 'nature', 'name': 'Nature', 'icon': '🌳', 'examples': ['tree', 'flower', 'rock']},
            {'id': 'characters', 'name': 'Characters', 'icon': '🧑', 'examples': ['robot', 'animal', 'creature']},
            {'id': 'food', 'name': 'Food', 'icon': '🍕', 'examples': ['pizza', 'cake', 'fruit']},
        ]

        return jsonify({
            'success': True,
            'categories': categories
        }), 200

    except Exception as e:
        log.error(f"Error getting categories: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 3D Model Generation ====================

@ai_3d_model_builder_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_3d_model():
    """
    Generate 3D model from text prompt.

    Request body:
    {
        "prompt_text": "a red sports car",
        "complexity_level": "simple|medium|detailed",
        "style": "realistic|cartoon|low_poly|clay|wireframe",
        "title": "My Car Model"
    }

    Returns:
        Task ID for progress tracking
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        # Validate required fields
        prompt_text = data.get('prompt_text', '').strip()
        if not prompt_text:
            return jsonify({'error': 'prompt_text is required'}), 400

        if len(prompt_text) < 10:
            return jsonify({'error': 'prompt_text must be at least 10 characters'}), 400

        # Get options with defaults
        complexity_level = data.get('complexity_level', 'simple')
        style = data.get('style', 'realistic')
        title = data.get('title', 'My 3D Model').strip()

        # Validate options
        valid_complexity = ['simple', 'medium', 'detailed']
        if complexity_level not in valid_complexity:
            return jsonify({'error': f'complexity_level must be one of: {valid_complexity}'}), 400

        service = AI3DModelBuilderService()
        available_styles = [s['id'] for s in service.get_available_styles()]
        if style not in available_styles:
            return jsonify({'error': f'style must be one of: {available_styles}'}), 400

        # Create progress record
        progress_id = str(uuid.uuid4())

        progress = Progress(
            id=progress_id,
            user_id=user_id,
            file_id=None,
            tool='ai_3d_model_builder',
            status='pending',
            percentage=0,
            created_at=datetime.utcnow()
        )

        db.session.add(progress)
        db.session.commit()

        log.info(f"[AI3DModelBuilderAPI] Created progress record {progress_id} for user {user_id}")

        # Queue the Celery task
        task_options = {
            'prompt_text': prompt_text,
            'complexity_level': complexity_level,
            'style': style,
            'title': title
        }

        task = generate_3d_model_task.delay(
            user_id=user_id,
            progress_id=progress_id,
            options=task_options
        )

        log.info(f"[AI3DModelBuilderAPI] Queued 3D model generation task {task.id} for progress {progress_id}")

        return jsonify({
            'task_id': task.id,
            'progress_id': progress_id,
            'status': 'pending',
            'message': '3D model generation started successfully',
            'options_used': task_options
        }), 202

    except Exception as e:
        log.error(f"[AI3DModelBuilderAPI] Error starting 3D model generation: {str(e)}")
        return jsonify({
            'error': 'Failed to start 3D model generation',
            'details': str(e)
        }), 500


@ai_3d_model_builder_bp.route('/progress/<uuid:progress_id>', methods=['GET'])
def get_generation_progress(progress_id):
    """
    Get progress of 3D model generation task.

    Returns status, percentage, and current step.
    """
    try:
        progress = db.session.query(Progress).filter(Progress.id == progress_id).first()

        if not progress:
            return jsonify({'error': 'Progress record not found'}), 404

        response = {
            'progress_id': str(progress.id),
            'status': progress.status,
            'percentage': progress.percentage or 0,
            'tool': progress.tool,
            'user_id': progress.user_id,
            'created_at': progress.created_at.isoformat() if progress.created_at else None,
            'updated_at': progress.updated_at.isoformat() if progress.updated_at else None
        }

        # Add completion timestamp if completed
        if progress.completed_at:
            response['completed_at'] = progress.completed_at.isoformat()

        # Add error message if failed
        if progress.status == 'failed' and progress.error_message:
            response['error_message'] = progress.error_message

        # Add result data if completed
        if progress.status == 'completed' and progress.result_data:
            response['result'] = progress.result_data

        return jsonify(response)

    except Exception as e:
        log.error(f"[AI3DModelBuilderAPI] Error getting progress for {progress_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve progress',
            'details': str(e)
        }), 500


# ==================== Gallery & Model Management ====================

@ai_3d_model_builder_bp.route('/gallery', methods=['GET'])
@jwt_required()
def get_3d_models_gallery():
    """
    Get user's 3D models gallery.

    Query parameters:
    - page: Page number (default 1)
    - per_page: Items per page (default 20, max 100)
    - category: Filter by category (optional)
    - style: Filter by style (optional)

    Returns:
    - List of 3D models with thumbnails and metadata
    - Pagination info
    """
    try:
        user_id = get_jwt_identity()

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        category = request.args.get('category')
        style = request.args.get('style')

        # Calculate offset
        offset = (page - 1) * per_page

        # Get models for user
        models = ThreeDModelCreation.get_user_models(
            user_id=user_id,
            limit=per_page,
            offset=offset,
            category=category,
            style=style
        )

        total_count = ThreeDModelCreation.get_user_models_count(
            user_id=user_id,
            category=category,
            style=style
        )

        # Convert to dictionaries (without full files data for gallery view)
        models_data = [model.to_dict(include_files=False) for model in models]

        return jsonify({
            'models': models_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_models': total_count,
                'total_pages': (total_count + per_page - 1) // per_page
            }
        })

    except Exception as e:
        log.error(f"[AI3DModelBuilderAPI] Error getting gallery: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve 3D models gallery',
            'details': str(e)
        }), 500


@ai_3d_model_builder_bp.route('/models/<uuid:model_id>', methods=['GET'])
@jwt_required()
def get_3d_model_details(model_id):
    """
    Get full 3D model details by ID.

    Returns:
    - Complete model data including all file URLs and metadata
    """
    try:
        user_id = get_jwt_identity()

        # Get model from database
        model = ThreeDModelCreation.query.filter_by(
            id=model_id,
            user_id=user_id
        ).first()

        if not model:
            return jsonify({'error': '3D model not found or access denied'}), 404

        # Return full model data
        return jsonify(model.to_dict(include_files=True))

    except Exception as e:
        log.error(f"[AI3DModelBuilderAPI] Error getting model {model_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve 3D model',
            'details': str(e)
        }), 500


@ai_3d_model_builder_bp.route('/models/<uuid:model_id>/download', methods=['GET'])
@jwt_required()
def download_3d_model(model_id):
    """
    Download 3D model file.

    Query parameters:
    - format: glb|obj|stl (default: glb)

    Returns:
    - 3D model file as binary download
    """
    try:
        user_id = get_jwt_identity()

        # Get format parameter
        file_format = request.args.get('format', 'glb').lower()
        valid_formats = ['glb', 'obj', 'stl']

        if file_format not in valid_formats:
            return jsonify({'error': f'format must be one of: {valid_formats}'}), 400

        # Get model from database
        model = ThreeDModelCreation.query.filter_by(
            id=model_id,
            user_id=user_id
        ).first()

        if not model:
            return jsonify({'error': '3D model not found or access denied'}), 404

        # Get file URL from model_files
        file_url = model.model_files.get(f'{file_format}_url')

        if not file_url:
            return jsonify({'error': f'{file_format.upper()} file not available for this model'}), 400

        # Download from Azure
        log.info(f"[AI3DModelBuilderAPI] Downloading {file_format.upper()} for {model_id} from Azure")
        response = requests.get(file_url, timeout=60)
        response.raise_for_status()

        # Create file-like object
        file_bytes = BytesIO(response.content)

        # Generate filename
        safe_title = "".join(c for c in model.title if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{safe_title}.{file_format}" if safe_title else f"model_{model_id}.{file_format}"

        # Set MIME type
        mime_types = {
            'glb': 'model/gltf-binary',
            'obj': 'model/obj',
            'stl': 'model/stl'
        }

        log.info(f"[AI3DModelBuilderAPI] Sending {file_format.upper()} download: {filename}")

        # Send file
        return send_file(
            file_bytes,
            mimetype=mime_types.get(file_format, 'application/octet-stream'),
            as_attachment=True,
            download_name=filename
        )

    except requests.exceptions.RequestException as e:
        log.error(f"[AI3DModelBuilderAPI] Error downloading from Azure: {str(e)}")
        return jsonify({
            'error': 'Failed to download model from storage',
            'details': str(e)
        }), 500

    except Exception as e:
        log.error(f"[AI3DModelBuilderAPI] Error downloading model {model_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to download 3D model',
            'details': str(e)
        }), 500


@ai_3d_model_builder_bp.route('/models/<uuid:model_id>', methods=['DELETE'])
@jwt_required()
def delete_3d_model_endpoint(model_id):
    """
    Delete a 3D model creation.

    Deletes both the database record and Azure storage files.

    Returns:
    - Success status
    """
    try:
        user_id = get_jwt_identity()

        log.info(f"[AI3DModelBuilderAPI] Deleting 3D model {model_id} for user {user_id}")

        # Delete model using storage service
        result = delete_3d_model(user_id, str(model_id))

        if result.get('success'):
            return jsonify({
                'message': '3D model deleted successfully',
                'model_id': str(model_id)
            })
        else:
            return jsonify({
                'error': result.get('error', 'Failed to delete 3D model')
            }), 400

    except Exception as e:
        log.error(f"[AI3DModelBuilderAPI] Error deleting model {model_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to delete 3D model',
            'details': str(e)
        }), 500


# ==================== User Stats ====================

@ai_3d_model_builder_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    """Get user's 3D model statistics."""
    try:
        user_id = get_jwt_identity()

        # Get categories used
        categories = ThreeDModelCreation.get_user_categories(user_id)

        # Get total count
        total_models = ThreeDModelCreation.get_user_models_count(user_id)

        # Get count by style
        styles_count = {}
        service = AI3DModelBuilderService()
        for style in service.get_available_styles():
            count = ThreeDModelCreation.get_user_models_count(user_id, style=style['id'])
            if count > 0:
                styles_count[style['id']] = count

        return jsonify({
            'total_models': total_models,
            'categories': categories,
            'styles_count': styles_count
        })

    except Exception as e:
        log.error(f"[AI3DModelBuilderAPI] Error getting user stats: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve statistics',
            'details': str(e)
        }), 500


@ai_3d_model_builder_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for AI 3D model builder service."""
    return jsonify({
        'service': 'ai_3d_model_builder',
        'status': 'healthy',
        'stage': 1,
        'timestamp': datetime.utcnow().isoformat()
    })


# Error handlers
@ai_3d_model_builder_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@ai_3d_model_builder_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
