# app/routes/stages/create/data_story_builder_routes.py
"""
Data Story Builder Routes

API endpoints for the Data Story Builder tool in the Create stage.
"""

import logging
import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError

from app.db import db
from app.models.status import Progress
from app.models.data_stories import DataStoryCreation
from app.models.files import UploadedFile
from app.tasks.data_story_builder_tasks import generate_data_story_stage_1, generate_data_story_stage_2

logger = logging.getLogger(__name__)

data_story_builder_bp = Blueprint(
    'data_story_builder',
    __name__,
    url_prefix='/api/data_story_builder'
)


@data_story_builder_bp.route('/start_stage_1', methods=['POST'])
@jwt_required()
def start_stage_1():
    """
    Start Stage 1: Profile dataset and generate AI insights.

    Request body:
    {
        "file_id": "uuid-of-uploaded-file",
        "title": "Q4 Sales Analysis"
    }

    Returns:
    {
        "progress_id": "uuid",
        "message": "Stage 1 started successfully"
    }
    """
    try:
        # Get user_id from JWT token
        user_id = get_jwt_identity()
        
        data = request.get_json()

        # Validate required fields
        file_id = data.get('file_id')
        title = data.get('title', 'Untitled Data Story')

        if not file_id:
            return jsonify({
                'success': False,
                'error': 'file_id is required'
            }), 400

        logger.info(f"Starting Stage 1 for user {user_id}, file {file_id}")

        # Validate file exists and is CSV/Excel
        uploaded_file = UploadedFile.query.get(file_id)
        if not uploaded_file:
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404

        if uploaded_file.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized access to file'
            }), 403

        filename = uploaded_file.original_file_name.lower()
        if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
            return jsonify({
                'success': False,
                'error': 'Only CSV and Excel files are supported'
            }), 400

        # Create progress record
        progress_id = str(uuid.uuid4())
        progress = Progress(
            id=progress_id,
            user_id=user_id,
            tool='data_story_builder',
            status='pending',
            percentage=0
        )

        db.session.add(progress)
        db.session.commit()

        logger.info(f"Created progress record: {progress_id}")

        # Start Stage 1 task
        generate_data_story_stage_1.delay(
            progress_id,
            user_id,
            file_id,
            title
        )

        return jsonify({
            'success': True,
            'progress_id': progress_id,
            'message': 'Stage 1 started successfully'
        }), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in start_stage_1: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error occurred'
        }), 500

    except Exception as e:
        logger.error(f"Error in start_stage_1: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_story_builder_bp.route('/start_stage_2', methods=['POST'])
@jwt_required()
def start_stage_2():
    """
    Start Stage 2: Generate visualizations and export.

    Request body:
    {
        "data_story_id": "uuid",
        "selected_charts": [
            {
                "chart_type": "line",
                "title": "Revenue Over Time",
                "x_column": "date",
                "y_column": "revenue"
            }
        ]
    }

    Returns:
    {
        "progress_id": "uuid",
        "message": "Stage 2 started successfully"
    }
    """
    try:
        # Get user_id from JWT token
        user_id = get_jwt_identity()
        
        data = request.get_json()

        # Validate required fields
        data_story_id = data.get('data_story_id')
        selected_charts = data.get('selected_charts', [])

        if not data_story_id:
            return jsonify({
                'success': False,
                'error': 'data_story_id is required'
            }), 400

        if not selected_charts:
            return jsonify({
                'success': False,
                'error': 'At least one chart must be selected'
            }), 400

        logger.info(f"Starting Stage 2 for story {data_story_id}, {len(selected_charts)} charts")

        # Validate data story exists
        data_story = DataStoryCreation.query.get(data_story_id)
        if not data_story:
            return jsonify({
                'success': False,
                'error': 'Data story not found'
            }), 404

        if data_story.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized access to data story'
            }), 403

        if data_story.current_stage != 1:
            return jsonify({
                'success': False,
                'error': 'Stage 1 must be completed before starting Stage 2'
            }), 400

        # Create progress record
        progress_id = str(uuid.uuid4())
        progress = Progress(
            id=progress_id,
            user_id=user_id,
            tool='data_story_builder',
            status='pending',
            percentage=0
        )

        db.session.add(progress)
        db.session.commit()

        logger.info(f"Created progress record: {progress_id}")

        # Start Stage 2 task
        generate_data_story_stage_2.delay(
            progress_id,
            user_id,
            data_story_id,
            selected_charts
        )

        return jsonify({
            'success': True,
            'progress_id': progress_id,
            'message': 'Stage 2 started successfully'
        }), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in start_stage_2: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error occurred'
        }), 500

    except Exception as e:
        logger.error(f"Error in start_stage_2: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_story_builder_bp.route('/progress/<progress_id>', methods=['GET'])
def get_progress(progress_id):
    """
    Get progress status for a data story generation task.

    Returns:
    {
        "status": "pending|in_progress|completed|failed",
        "percentage": 0-100,
        "result_data": {...},
        "error_message": "..."
    }
    """
    try:
        progress = Progress.query.get(progress_id)

        if not progress:
            return jsonify({
                'success': False,
                'error': 'Progress record not found'
            }), 404

        return jsonify({
            'success': True,
            'status': progress.status,
            'percentage': progress.percentage,
            'result_data': progress.result_data,
            'error_message': progress.error_message
        }), 200

    except Exception as e:
        logger.error(f"Error in get_progress: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_story_builder_bp.route('/gallery', methods=['GET'])
@jwt_required()
def get_gallery():
    """
    Get user's data story gallery.

    Query params:
        - limit: Optional (default: 20)
        - offset: Optional (default: 0)

    Returns:
    {
        "stories": [...],
        "total": 42
    }
    """
    try:
        # Get user_id from JWT token
        user_id = get_jwt_identity()
        
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)

        # Get stories
        stories = DataStoryCreation.get_user_stories(user_id, limit=limit, offset=offset)
        total = DataStoryCreation.get_user_stories_count(user_id)

        # Convert to dict (without full data)
        stories_data = [story.to_dict(include_full_data=False) for story in stories]

        return jsonify({
            'success': True,
            'stories': stories_data,
            'total': total
        }), 200

    except Exception as e:
        logger.error(f"Error in get_gallery: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@data_story_builder_bp.route('/story/<story_id>', methods=['GET'])
@jwt_required()
def get_story(story_id):
    """
    Get full data story details.

    Returns:
    {
        "story": {...}  // Full story data including profile, insights, visualizations
    }
    """
    try:
        # Get user_id from JWT token
        user_id = get_jwt_identity()

        story = DataStoryCreation.query.get(story_id)

        if not story:
            return jsonify({
                'success': False,
                'error': 'Story not found'
            }), 404

        if story.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized access'
            }), 403

        # Return full data
        story_data = story.to_dict(include_full_data=True)

        return jsonify({
            'success': True,
            'story': story_data
        }), 200

    except Exception as e:
        logger.error(f"Error in get_story: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_story_builder_bp.route('/story/<story_id>', methods=['DELETE'])
@jwt_required()
def delete_story(story_id):
    """
    Delete a data story and its Azure files.

    Returns:
    {
        "success": true,
        "message": "Story deleted successfully"
    }
    """
    try:
        # Get user_id from JWT token
        user_id = get_jwt_identity()

        story = DataStoryCreation.query.get(story_id)

        if not story:
            return jsonify({
                'success': False,
                'error': 'Story not found'
            }), 404

        if story.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized access'
            }), 403

        # Delete Azure files
        try:
            from app.services.data_story_storage_service import DataStoryStorageService
            storage_service = DataStoryStorageService()
            storage_service.delete_story_folder(user_id, story_id)
            logger.info(f"Deleted Azure files for story {story_id}")
        except Exception as e:
            logger.error(f"Error deleting Azure files: {str(e)}")
            # Continue with DB deletion even if Azure deletion fails

        # Delete from database
        db.session.delete(story)
        db.session.commit()

        logger.info(f"Deleted story {story_id}")

        return jsonify({
            'success': True,
            'message': 'Story deleted successfully'
        }), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_story: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error occurred'
        }), 500

    except Exception as e:
        logger.error(f"Error in delete_story: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_story_builder_bp.route('/story/<story_id>/update_title', methods=['PUT'])
@jwt_required()
def update_title(story_id):
    """
    Update a data story's title.

    Request body:
    {
        "title": "New Title"
    }

    Returns:
    {
        "success": true,
        "message": "Title updated successfully"
    }
    """
    try:
        # Get user_id from JWT token
        user_id = get_jwt_identity()
        
        data = request.get_json()
        new_title = data.get('title')

        if not new_title:
            return jsonify({
                'success': False,
                'error': 'title is required'
            }), 400

        story = DataStoryCreation.query.get(story_id)

        if not story:
            return jsonify({
                'success': False,
                'error': 'Story not found'
            }), 404

        if story.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized access'
            }), 403

        story.title = new_title
        db.session.commit()

        logger.info(f"Updated title for story {story_id}")

        return jsonify({
            'success': True,
            'message': 'Title updated successfully'
        }), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in update_title: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error occurred'
        }), 500

    except Exception as e:
        logger.error(f"Error in update_title: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500