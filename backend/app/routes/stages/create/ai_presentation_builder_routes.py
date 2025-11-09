from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.status import Progress
from app.models.presentations import PresentationCreation
from app.db import db
from app.tasks.ai_presentation_builder_tasks import (
    generate_presentation_content_task,
    finalize_presentation_task
)
from app.services.presentation_storage_service import delete_presentation
from app.services.stages.create.ai_presentation_builder_service import AIPresentationBuilderService
import uuid
from datetime import datetime
import logging
import requests
from io import BytesIO

# Set up logging
log = logging.getLogger(__name__)

# Create Blueprint
ai_presentation_builder_bp = Blueprint('ai_presentation_builder', __name__)


@ai_presentation_builder_bp.route('/generate-content', methods=['POST'])
@jwt_required()
def generate_presentation_content():
    """
    Start Stage 1: Generate presentation slide content with ChatGPT.

    Expected JSON payload:
    {
        "source_type": "file|vault|text",
        "file_id": "uuid",  # Optional, for file/vault sources
        "text_prompt": "presentation topic",  # Optional, for text source
        "total_slides": 10,  # Number of slides (5-20, default 10)
        "theme": "professional_blue"  # Theme ID
    }

    Returns:
    - task_id: Celery task ID
    - progress_id: Progress tracking ID
    - status: Task status
    """
    try:
        # Get authenticated user from JWT token
        user_id = get_jwt_identity()

        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        source_type = data.get('source_type')
        if not source_type or source_type not in ['file', 'vault', 'text']:
            return jsonify({'error': 'source_type must be one of: file, vault, text'}), 400

        # Validate source-specific requirements
        if source_type in ['file', 'vault']:
            file_id = data.get('file_id')
            if not file_id:
                return jsonify({'error': 'file_id is required for file/vault sources'}), 400

            # Validate that file exists
            from app.models.files import UploadedFile
            file_obj = db.session.query(UploadedFile).filter(UploadedFile.id == file_id).first()
            if not file_obj:
                return jsonify({'error': f'File not found: {file_id}'}), 404

        elif source_type == 'text':
            text_prompt = data.get('text_prompt', '').strip()
            if not text_prompt:
                return jsonify({'error': 'text_prompt is required for text source'}), 400
            if len(text_prompt) < 20:
                return jsonify({'error': 'text_prompt must be at least 20 characters'}), 400
            file_id = None

        # Presentation generation options
        total_slides = data.get('total_slides', 10)
        theme = data.get('theme', 'professional_blue')

        # Validate options
        if not isinstance(total_slides, int) or total_slides < 5 or total_slides > 20:
            return jsonify({'error': 'total_slides must be between 5 and 20'}), 400

        # Validate theme exists
        service = AIPresentationBuilderService()
        available_themes = [t['id'] for t in service.get_available_themes()]
        if theme not in available_themes:
            return jsonify({'error': f'Invalid theme. Available themes: {available_themes}'}), 400

        # Create progress record
        progress_id = str(uuid.uuid4())

        progress = Progress(
            id=progress_id,
            user_id=user_id,
            file_id=file_id,
            tool='ai_presentation_builder',
            status='pending',
            percentage=0,
            created_at=datetime.utcnow()
        )

        db.session.add(progress)
        db.session.commit()

        log.info(f"[PresentationBuilderAPI] Created progress record {progress_id} for user {user_id}")

        # Queue the Celery task
        task_options = {
            'source_type': source_type,
            'text_prompt': data.get('text_prompt', ''),
            'total_slides': total_slides,
            'theme': theme
        }

        task = generate_presentation_content_task.delay(
            user_id=user_id,
            file_id=file_id,
            progress_id=progress_id,
            options=task_options
        )

        log.info(f"[PresentationBuilderAPI] Queued content generation task {task.id} for progress {progress_id}")

        return jsonify({
            'task_id': task.id,
            'progress_id': progress_id,
            'status': 'pending',
            'message': 'Presentation content generation started successfully',
            'stage': 1,
            'options_used': task_options
        }), 202

    except Exception as e:
        log.error(f"[PresentationBuilderAPI] Error starting content generation: {str(e)}")
        return jsonify({
            'error': 'Failed to start presentation content generation',
            'details': str(e)
        }), 500


@ai_presentation_builder_bp.route('/finalize', methods=['POST'])
@jwt_required()
def finalize_presentation():
    """
    Start Stage 2: Generate DALL-E images for selected slides and create PPTX file.

    Expected JSON payload:
    {
        "presentation_id": "uuid",  # ID from Stage 1
        "image_style": "professional|creative",  # DALL-E image style
        "slides_for_images": [1, 3, 5, 7]  # Slide numbers that should have images
    }

    Returns:
    - task_id: Celery task ID
    - progress_id: Progress tracking ID
    - status: Task status
    """
    try:
        # Get authenticated user from JWT token
        user_id = get_jwt_identity()

        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        presentation_id = data.get('presentation_id')
        if not presentation_id:
            return jsonify({'error': 'presentation_id is required'}), 400

        # Validate presentation exists and belongs to user
        presentation = PresentationCreation.query.filter_by(
            id=presentation_id,
            user_id=user_id
        ).first()

        if not presentation:
            return jsonify({'error': 'Presentation not found or access denied'}), 404

        # Validate options
        image_style = data.get('image_style', 'professional')
        if image_style not in ['professional', 'creative']:
            return jsonify({'error': 'image_style must be professional or creative'}), 400

        slides_for_images = data.get('slides_for_images', [])
        if not isinstance(slides_for_images, list):
            return jsonify({'error': 'slides_for_images must be an array of slide numbers'}), 400

        # Validate slide numbers
        if slides_for_images:
            max_slide = presentation.total_slides
            invalid_slides = [s for s in slides_for_images if s < 1 or s > max_slide]
            if invalid_slides:
                return jsonify({
                    'error': f'Invalid slide numbers: {invalid_slides}. Must be between 1 and {max_slide}'
                }), 400

        # Create progress record for Stage 2
        progress_id = str(uuid.uuid4())

        progress = Progress(
            id=progress_id,
            user_id=user_id,
            file_id=presentation.source_file_id,
            tool='ai_presentation_builder',
            status='pending',
            percentage=0,
            created_at=datetime.utcnow()
        )

        db.session.add(progress)
        db.session.commit()

        log.info(f"[PresentationBuilderAPI] Created Stage 2 progress {progress_id} for presentation {presentation_id}")

        # Queue the Celery task
        task_options = {
            'presentation_id': presentation_id,
            'image_style': image_style,
            'slides_for_images': slides_for_images
        }

        task = finalize_presentation_task.delay(
            user_id=user_id,
            progress_id=progress_id,
            options=task_options
        )

        log.info(f"[PresentationBuilderAPI] Queued finalization task {task.id} for progress {progress_id}")

        return jsonify({
            'task_id': task.id,
            'progress_id': progress_id,
            'status': 'pending',
            'message': 'Presentation finalization started successfully',
            'stage': 2,
            'options_used': task_options
        }), 202

    except Exception as e:
        log.error(f"[PresentationBuilderAPI] Error starting finalization: {str(e)}")
        return jsonify({
            'error': 'Failed to start presentation finalization',
            'details': str(e)
        }), 500


@ai_presentation_builder_bp.route('/progress/<uuid:progress_id>', methods=['GET'])
def get_presentation_progress(progress_id):
    """
    Get status information for presentation generation progress.

    Returns status, percentage, and current stage.
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

        # Add file_id if present
        if progress.file_id:
            response['file_id'] = str(progress.file_id)

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
        log.error(f"[PresentationBuilderAPI] Error getting progress for {progress_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve presentation progress',
            'details': str(e)
        }), 500


@ai_presentation_builder_bp.route('/gallery', methods=['GET'])
@jwt_required()
def get_presentations_gallery():
    """
    Get user's presentation creations gallery.

    Query parameters:
    - page: Page number (default 1)
    - per_page: Items per page (default 20, max 100)
    - status: Filter by status ('active' or 'orphaned', optional)

    Returns:
    - List of presentations with thumbnails and metadata
    - Pagination info
    """
    try:
        user_id = get_jwt_identity()

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status_filter = request.args.get('status')

        # Calculate offset
        offset = (page - 1) * per_page

        # Build query
        query = PresentationCreation.query.filter_by(user_id=user_id)

        # Apply status filter if provided
        if status_filter:
            if status_filter not in ['active', 'orphaned']:
                return jsonify({'error': 'status must be active or orphaned'}), 400
            query = query.filter_by(status=status_filter)

        # Get total count
        total_count = query.count()

        # Get presentations with pagination
        presentations = query.order_by(
            PresentationCreation.created_at.desc()
        ).limit(per_page).offset(offset).all()

        # Convert to dictionaries (without full slides data)
        presentations_data = []
        for pres in presentations:
            presentations_data.append({
                'id': str(pres.id),
                'user_id': pres.user_id,
                'title': pres.title,
                'source_type': pres.source_type,
                'source_file_id': str(pres.source_file_id) if pres.source_file_id else None,
                'status': pres.status,
                'total_slides': pres.total_slides,
                'theme': pres.theme,
                'image_style': pres.image_style,
                'thumbnail_url': pres.thumbnail_url,
                'pptx_url': pres.pptx_url,
                'created_at': pres.created_at.isoformat() if pres.created_at else None,
                'updated_at': pres.updated_at.isoformat() if pres.updated_at else None,
                'has_pptx': pres.pptx_url is not None,
                'preview_images_count': len(pres.preview_images) if pres.preview_images else 0
            })

        return jsonify({
            'presentations': presentations_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_presentations': total_count,
                'total_pages': (total_count + per_page - 1) // per_page
            }
        })

    except Exception as e:
        log.error(f"[PresentationBuilderAPI] Error getting gallery: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve presentations gallery',
            'details': str(e)
        }), 500


@ai_presentation_builder_bp.route('/presentations/<uuid:presentation_id>', methods=['GET'])
@jwt_required()
def get_presentation_by_id(presentation_id):
    """
    Get full presentation details by ID.

    Returns:
    - Complete presentation data including all slides with content and images
    """
    try:
        user_id = get_jwt_identity()

        # Get presentation from database
        presentation = PresentationCreation.query.filter_by(
            id=presentation_id,
            user_id=user_id
        ).first()

        if not presentation:
            return jsonify({'error': 'Presentation not found or access denied'}), 404

        # Return full presentation data
        return jsonify({
            'id': str(presentation.id),
            'user_id': presentation.user_id,
            'title': presentation.title,
            'source_type': presentation.source_type,
            'source_file_id': str(presentation.source_file_id) if presentation.source_file_id else None,
            'source_text_preview': presentation.source_text_preview,
            'status': presentation.status,
            'total_slides': presentation.total_slides,
            'theme': presentation.theme,
            'image_style': presentation.image_style,
            'azure_folder_path': presentation.azure_folder_path,
            'pptx_url': presentation.pptx_url,
            'thumbnail_url': presentation.thumbnail_url,
            'slides_data': presentation.slides_data,
            'preview_images': presentation.preview_images,
            'presentation_metadata': presentation.presentation_metadata,
            'created_at': presentation.created_at.isoformat() if presentation.created_at else None,
            'updated_at': presentation.updated_at.isoformat() if presentation.updated_at else None
        })

    except Exception as e:
        log.error(f"[PresentationBuilderAPI] Error getting presentation {presentation_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve presentation',
            'details': str(e)
        }), 500


@ai_presentation_builder_bp.route('/presentations/<uuid:presentation_id>/download', methods=['GET'])
@jwt_required()
def download_presentation(presentation_id):
    """
    Download PowerPoint file for a presentation.

    Returns:
    - PPTX file as binary download
    """
    try:
        user_id = get_jwt_identity()

        # Get presentation from database
        presentation = PresentationCreation.query.filter_by(
            id=presentation_id,
            user_id=user_id
        ).first()

        if not presentation:
            return jsonify({'error': 'Presentation not found or access denied'}), 404

        if not presentation.pptx_url:
            return jsonify({'error': 'PPTX file not yet generated. Complete Stage 2 first.'}), 400

        # Download from Azure
        log.info(f"[PresentationBuilderAPI] Downloading PPTX for {presentation_id} from Azure")
        response = requests.get(presentation.pptx_url, timeout=60)
        response.raise_for_status()

        # Create file-like object
        pptx_bytes = BytesIO(response.content)

        # Generate filename
        safe_title = "".join(c for c in presentation.title if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{safe_title}.pptx" if safe_title else f"presentation_{presentation_id}.pptx"

        log.info(f"[PresentationBuilderAPI] Sending PPTX download: {filename}")

        # Send file
        return send_file(
            pptx_bytes,
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
            as_attachment=True,
            download_name=filename
        )

    except requests.exceptions.RequestException as e:
        log.error(f"[PresentationBuilderAPI] Error downloading from Azure: {str(e)}")
        return jsonify({
            'error': 'Failed to download presentation from storage',
            'details': str(e)
        }), 500

    except Exception as e:
        log.error(f"[PresentationBuilderAPI] Error downloading presentation {presentation_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to download presentation',
            'details': str(e)
        }), 500


@ai_presentation_builder_bp.route('/presentations/<uuid:presentation_id>', methods=['DELETE'])
@jwt_required()
def delete_presentation_endpoint(presentation_id):
    """
    Delete a presentation creation.

    Deletes both the database record and Azure storage files.

    Returns:
    - Success status
    """
    try:
        user_id = get_jwt_identity()

        log.info(f"[PresentationBuilderAPI] Deleting presentation {presentation_id} for user {user_id}")

        # Delete presentation using storage service
        result = delete_presentation(user_id, str(presentation_id))

        if result.get('success'):
            return jsonify({
                'message': 'Presentation deleted successfully',
                'presentation_id': str(presentation_id)
            })
        else:
            return jsonify({
                'error': result.get('error', 'Failed to delete presentation')
            }), 400

    except Exception as e:
        log.error(f"[PresentationBuilderAPI] Error deleting presentation {presentation_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to delete presentation',
            'details': str(e)
        }), 500


@ai_presentation_builder_bp.route('/themes', methods=['GET'])
def get_themes():
    """
    Get list of available presentation themes.

    Returns:
    - List of themes with IDs, names, and color information
    """
    try:
        service = AIPresentationBuilderService()
        themes = service.get_available_themes()

        return jsonify({
            'themes': themes,
            'total_themes': len(themes)
        })

    except Exception as e:
        log.error(f"[PresentationBuilderAPI] Error getting themes: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve themes',
            'details': str(e)
        }), 500


@ai_presentation_builder_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for AI presentation builder service."""
    return jsonify({
        'service': 'ai_presentation_builder',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


# Error handlers
@ai_presentation_builder_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@ai_presentation_builder_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
