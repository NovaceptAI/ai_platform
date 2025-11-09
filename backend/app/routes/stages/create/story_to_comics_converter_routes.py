from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.status import Progress
from app.models.comics import ComicCreation
from app.db import db
from app.tasks.story_to_comics_converter_tasks import create_comic_task
from app.services.comic_storage_service import delete_comic_creation
import uuid
from datetime import datetime
import logging

# Set up logging
log = logging.getLogger(__name__)

# Create Blueprint
story_to_comics_bp = Blueprint('story_to_comics', __name__)

@story_to_comics_bp.route('/start', methods=['POST'])
@jwt_required()
def start_comic_creation():
    """
    Start story to comics conversion task.

    Expected JSON payload:
    {
        "source_type": "file|vault|text",
        "file_ids": ["uuid1", "uuid2"],  # Optional, for file/vault sources (max 3)
        "text_prompt": "story text here",  # Optional, for text source
        "num_panels": 6,  # Number of comic panels (1-12, default 6)
        "style": "vivid|natural",  # Image style
        "generate_images": true  # Whether to generate images
    }
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
            file_ids = data.get('file_ids', [])
            if not file_ids:
                return jsonify({'error': 'file_ids is required for file/vault sources'}), 400
            if len(file_ids) > 3:
                return jsonify({'error': 'Maximum 3 files can be processed at once'}), 400
        elif source_type == 'text':
            text_prompt = data.get('text_prompt', '').strip()
            if not text_prompt:
                return jsonify({'error': 'text_prompt is required for text source'}), 400
            if len(text_prompt) < 50:
                return jsonify({'error': 'text_prompt must be at least 50 characters'}), 400
            file_ids = []  # No files for text source

        # Comic generation options
        num_panels = data.get('num_panels', 6)
        image_style = data.get('style', 'vivid')  # 'vivid' or 'natural'
        generate_images = data.get('generate_images', True)

        # Validate options
        if not isinstance(num_panels, int) or num_panels < 1 or num_panels > 12:
            return jsonify({'error': 'num_panels must be between 1 and 12'}), 400

        valid_image_styles = ['vivid', 'natural']
        if image_style not in valid_image_styles:
            return jsonify({'error': f'style must be one of: {valid_image_styles}'}), 400

        # Validate that files exist (for file/vault sources)
        if source_type in ['file', 'vault']:
            from app.models.files import UploadedFile
            existing_files = db.session.query(UploadedFile).filter(UploadedFile.id.in_(file_ids)).all()
            existing_file_ids = [f.id for f in existing_files]

            if len(existing_file_ids) != len(file_ids):
                missing_files = set(file_ids) - set(existing_file_ids)
                return jsonify({
                    'error': f'Files not found: {list(missing_files)}',
                    'found_files': existing_file_ids
                }), 404

        # Create progress record
        progress_id = str(uuid.uuid4())

        # Set file_id if only one file is being processed
        file_id_for_progress = file_ids[0] if len(file_ids) == 1 else None

        progress = Progress(
            id=progress_id,
            user_id=user_id,
            file_id=file_id_for_progress,
            tool='story_to_comics',
            status='pending',
            percentage=0,
            created_at=datetime.utcnow()
        )

        db.session.add(progress)
        db.session.commit()

        log.info(f"[StoryToComicsAPI] Created progress record {progress_id} for user {user_id}")

        # Queue the Celery task
        task_options = {
            'source_type': source_type,
            'text_prompt': data.get('text_prompt', ''),
            'num_panels': num_panels,
            'image_style': image_style,
            'generate_images': generate_images
        }

        task = create_comic_task.delay(
            user_id=user_id,
            file_ids=file_ids,
            progress_id=progress_id,
            options=task_options
        )

        log.info(f"[StoryToComicsAPI] Queued comic creation task {task.id} for progress {progress_id}")

        return jsonify({
            'task_id': task.id,
            'progress_id': progress_id,
            'status': 'pending',
            'message': 'Comic creation task started successfully',
            'options_used': task_options,
            'sources_count': len(file_ids) if file_ids else 1
        }), 202

    except Exception as e:
        log.error(f"[StoryToComicsAPI] Error starting comic creation: {str(e)}")
        return jsonify({
            'error': 'Failed to start comic creation task',
            'details': str(e)
        }), 500


@story_to_comics_bp.route('/results', methods=['GET'])
def get_comic_results():
    """
    Get comic creation results by progress ID or file ID.

    Query parameters:
    - progress_id: UUID of the progress record
    - file_id: UUID of the file (will get latest completed progress)

    Returns:
    - If pending/in_progress: Current progress status
    - If completed: Full comic results
    - If failed: Error information
    """
    try:
        progress_id = request.args.get('progress_id')
        file_id = request.args.get('file_id')

        if not progress_id and not file_id:
            return jsonify({'error': 'Either progress_id or file_id is required'}), 400

        # Get progress record
        if progress_id:
            progress = db.session.query(Progress).filter(Progress.id == progress_id).first()
        else:
            # Get the latest progress for this file
            progress = db.session.query(Progress).filter(
                Progress.file_id == file_id,
                Progress.tool == 'story_to_comics',
                Progress.status == 'completed'
            ).order_by(Progress.created_at.desc()).first()

            # If no completed progress found, get the latest one (any status)
            if not progress:
                progress = db.session.query(Progress).filter(
                    Progress.file_id == file_id,
                    Progress.tool == 'story_to_comics'
                ).order_by(Progress.created_at.desc()).first()

        if not progress:
            return jsonify({'error': 'No results found'}), 404

        # Return different responses based on status
        if progress.status == 'pending' or progress.status == 'in_progress':
            return jsonify({
                'progress_id': str(progress.id),
                'status': progress.status,
                'percentage': progress.percentage or 0,
                'message': 'Comic creation is still in progress',
                'tool': progress.tool,
                'user_id': progress.user_id,
                'created_at': progress.created_at.isoformat() if progress.created_at else None,
                'updated_at': progress.updated_at.isoformat() if progress.updated_at else None
            }), 202

        elif progress.status == 'failed':
            return jsonify({
                'progress_id': str(progress.id),
                'status': 'failed',
                'error': progress.error_message or 'Comic creation failed',
                'tool': progress.tool,
                'user_id': progress.user_id,
                'percentage': progress.percentage or 0,
                'created_at': progress.created_at.isoformat() if progress.created_at else None,
                'updated_at': progress.updated_at.isoformat() if progress.updated_at else None,
                'completed_at': progress.completed_at.isoformat() if progress.completed_at else None
            }), 500

        elif progress.status == 'completed':
            result_data = progress.result_data or {}

            return jsonify({
                'progress_id': str(progress.id),
                'status': progress.status,
                'comics': result_data.get('comics', []),
                'total_comics': result_data.get('total_comics', 0),
                'metadata': result_data.get('metadata', {}),
                'tool': progress.tool,
                'user_id': progress.user_id,
                'percentage': progress.percentage or 100,
                'created_at': progress.created_at.isoformat() if progress.created_at else None,
                'updated_at': progress.updated_at.isoformat() if progress.updated_at else None,
                'completed_at': progress.completed_at.isoformat() if progress.completed_at else None
            })

        else:
            return jsonify({
                'progress_id': str(progress.id),
                'status': progress.status,
                'percentage': progress.percentage or 0,
                'tool': progress.tool,
                'user_id': progress.user_id,
                'message': f'Unknown status: {progress.status}',
                'created_at': progress.created_at.isoformat() if progress.created_at else None,
                'updated_at': progress.updated_at.isoformat() if progress.updated_at else None
            }), 400

    except Exception as e:
        log.error(f"[StoryToComicsAPI] Error getting results: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve comic results',
            'details': str(e)
        }), 500


@story_to_comics_bp.route('/progress/<uuid:progress_id>', methods=['GET'])
def get_comic_creation_status(progress_id):
    """
    Get brief status information for comic creation progress.

    Returns only status, percentage, and current step - lighter weight than full results.
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

        return jsonify(response)

    except Exception as e:
        log.error(f"[StoryToComicsAPI] Error getting status for {progress_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve comic creation status',
            'details': str(e)
        }), 500


@story_to_comics_bp.route('/gallery', methods=['GET'])
@jwt_required()
def get_comics_gallery():
    """
    Get user's comic creations gallery.

    Query parameters:
    - page: Page number (default 1)
    - per_page: Items per page (default 20, max 100)

    Returns:
    - List of comics with thumbnails and metadata
    - Pagination info
    """
    try:
        user_id = get_jwt_identity()

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)

        # Calculate offset
        offset = (page - 1) * per_page

        # Get comics for user
        comics = ComicCreation.get_user_comics(user_id, limit=per_page, offset=offset)
        total_count = ComicCreation.get_user_comics_count(user_id)

        # Convert to dictionaries (without full panels data)
        comics_data = [comic.to_dict(include_panels=False) for comic in comics]

        return jsonify({
            'comics': comics_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_comics': total_count,
                'total_pages': (total_count + per_page - 1) // per_page
            }
        })

    except Exception as e:
        log.error(f"[StoryToComicsAPI] Error getting gallery: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve comics gallery',
            'details': str(e)
        }), 500


@story_to_comics_bp.route('/comics/<uuid:comic_id>', methods=['GET'])
@jwt_required()
def get_comic_by_id(comic_id):
    """
    Get full comic details by ID.

    Returns:
    - Complete comic data including all panels with Azure URLs
    """
    try:
        user_id = get_jwt_identity()

        # Get comic from database
        comic = ComicCreation.query.filter_by(
            id=comic_id,
            user_id=user_id
        ).first()

        if not comic:
            return jsonify({'error': 'Comic not found or access denied'}), 404

        # Return full comic data with panels
        return jsonify(comic.to_dict(include_panels=True))

    except Exception as e:
        log.error(f"[StoryToComicsAPI] Error getting comic {comic_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve comic',
            'details': str(e)
        }), 500


@story_to_comics_bp.route('/comics/<uuid:comic_id>', methods=['DELETE'])
@jwt_required()
def delete_comic(comic_id):
    """
    Delete a comic creation.

    Deletes both the database record and Azure storage files.

    Returns:
    - Success status
    """
    try:
        user_id = get_jwt_identity()

        log.info(f"[StoryToComicsAPI] Deleting comic {comic_id} for user {user_id}")

        # Delete comic using storage service
        result = delete_comic_creation(user_id, str(comic_id))

        if result.get('success'):
            return jsonify({
                'message': 'Comic deleted successfully',
                'comic_id': str(comic_id)
            })
        else:
            return jsonify({
                'error': result.get('error', 'Failed to delete comic')
            }), 400

    except Exception as e:
        log.error(f"[StoryToComicsAPI] Error deleting comic {comic_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to delete comic',
            'details': str(e)
        }), 500


@story_to_comics_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for story to comics service."""
    return jsonify({
        'service': 'story_to_comics',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


# Error handlers
@story_to_comics_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@story_to_comics_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
