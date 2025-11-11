"""
Learn by Drawing API Routes

REST API for educational drawing analysis.
"""

import logging
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from celery.result import AsyncResult
from app.db import db
from app.models.learning_drawings import LearningDrawing
from app.services.stages.create.learn_by_drawing_service import LearnByDrawingService
from app.services.learning_drawing_storage_service import delete_drawing_from_azure
from app.tasks.learn_by_drawing_tasks import analyze_drawing_task
import uuid

logger = logging.getLogger(__name__)

# Create blueprint
learn_by_drawing_bp = Blueprint('learn_by_drawing', __name__)


@learn_by_drawing_bp.route('/info', methods=['GET'])
@jwt_required()
def get_service_info():
    """Get service information and available topics."""
    try:
        service = LearnByDrawingService()
        info = service.get_service_info()
        return jsonify(info), 200

    except Exception as e:
        logger.error(f"Error getting service info: {str(e)}")
        return jsonify({'error': str(e)}), 500


@learn_by_drawing_bp.route('/topics', methods=['GET'])
@jwt_required()
def get_topics():
    """Get available learning topics."""
    try:
        service = LearnByDrawingService()
        topics = service.get_available_topics()
        return jsonify({'topics': topics}), 200

    except Exception as e:
        logger.error(f"Error getting topics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@learn_by_drawing_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze_drawing():
    """
    Start drawing analysis (async).

    Request body:
    {
        "image_data": "data:image/png;base64,...",
        "topic": "water_cycle",
        "age_group": "8-10",
        "title": "My Water Cycle Drawing",
        "canvas_width": 800,
        "canvas_height": 600
    }

    Returns:
    {
        "progress_id": "uuid",
        "task_id": "celery-task-id"
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # Validate required fields
        if not data.get('image_data'):
            return jsonify({'error': 'image_data is required'}), 400

        if not data.get('topic'):
            return jsonify({'error': 'topic is required'}), 400

        # Generate progress ID
        progress_id = str(uuid.uuid4())

        # Start async task
        task = analyze_drawing_task.delay(user_id, progress_id, data)

        logger.info(f"Started drawing analysis task {task.id} for user {user_id}")

        return jsonify({
            'progress_id': progress_id,
            'task_id': task.id
        }), 202

    except Exception as e:
        logger.error(f"Error starting analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500


@learn_by_drawing_bp.route('/progress/<progress_id>', methods=['GET'])
@jwt_required()
def get_progress(progress_id):
    """
    Get analysis progress.

    Returns:
    {
        "state": "PROGRESS" | "SUCCESS" | "FAILURE",
        "progress": 0-100,
        "status": "Analyzing drawing...",
        "result": {...}  // Only present when SUCCESS
    }
    """
    try:
        # Find task by progress_id (stored in meta)
        # Note: This is a simplified approach. In production, you might want
        # to store progress_id -> task_id mapping in Redis or database
        task_id = request.args.get('task_id')

        if not task_id:
            return jsonify({'error': 'task_id required'}), 400

        task_result = AsyncResult(task_id)

        if task_result.state == 'PENDING':
            response = {
                'state': 'PENDING',
                'progress': 0,
                'status': 'Waiting to start...'
            }
        elif task_result.state == 'PROGRESS':
            response = {
                'state': 'PROGRESS',
                'progress': task_result.info.get('progress', 0),
                'status': task_result.info.get('status', 'Processing...')
            }
        elif task_result.state == 'SUCCESS':
            response = {
                'state': 'SUCCESS',
                'progress': 100,
                'status': 'Analysis complete!',
                'result': task_result.result
            }
        else:  # FAILURE
            response = {
                'state': 'FAILURE',
                'progress': 0,
                'status': 'Analysis failed',
                'error': str(task_result.info)
            }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}")
        return jsonify({'error': str(e)}), 500


@learn_by_drawing_bp.route('/gallery', methods=['GET'])
@jwt_required()
def get_gallery():
    """
    Get user's drawing gallery.

    Query params:
    - topic: Filter by topic (optional)
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)

    Returns:
    {
        "drawings": [...],
        "total": 123,
        "topics_summary": [...]
    }
    """
    try:
        user_id = get_jwt_identity()
        topic = request.args.get('topic')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        # Get drawings
        drawings = LearningDrawing.get_user_drawings(user_id, topic, limit, offset)
        total = LearningDrawing.get_user_drawings_count(user_id, topic)

        # Get topics summary
        topics_summary = LearningDrawing.get_user_topics_summary(user_id)

        return jsonify({
            'drawings': [d.to_dict() for d in drawings],
            'total': total,
            'topics_summary': topics_summary
        }), 200

    except Exception as e:
        logger.error(f"Error getting gallery: {str(e)}")
        return jsonify({'error': str(e)}), 500


@learn_by_drawing_bp.route('/drawings/<drawing_id>', methods=['GET'])
@jwt_required()
def get_drawing(drawing_id):
    """Get specific drawing by ID."""
    try:
        user_id = get_jwt_identity()

        drawing = LearningDrawing.query.filter_by(id=drawing_id, user_id=user_id).first()

        if not drawing:
            return jsonify({'error': 'Drawing not found'}), 404

        return jsonify(drawing.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting drawing: {str(e)}")
        return jsonify({'error': str(e)}), 500


@learn_by_drawing_bp.route('/drawings/<drawing_id>', methods=['PATCH'])
@jwt_required()
def update_drawing(drawing_id):
    """
    Update drawing (e.g., toggle favorite, update title).

    Request body:
    {
        "title": "New Title",
        "is_favorite": true
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        drawing = LearningDrawing.query.filter_by(id=drawing_id, user_id=user_id).first()

        if not drawing:
            return jsonify({'error': 'Drawing not found'}), 404

        # Update allowed fields
        if 'title' in data:
            drawing.title = data['title']

        if 'is_favorite' in data:
            drawing.is_favorite = data['is_favorite']

        db.session.commit()

        return jsonify(drawing.to_dict()), 200

    except Exception as e:
        logger.error(f"Error updating drawing: {str(e)}")
        return jsonify({'error': str(e)}), 500


@learn_by_drawing_bp.route('/drawings/<drawing_id>', methods=['DELETE'])
@jwt_required()
def delete_drawing(drawing_id):
    """Delete drawing."""
    try:
        user_id = get_jwt_identity()

        drawing = LearningDrawing.query.filter_by(id=drawing_id, user_id=user_id).first()

        if not drawing:
            return jsonify({'error': 'Drawing not found'}), 404

        # Delete from Azure
        delete_drawing_from_azure(drawing.drawing_image_url)

        # Delete from database
        db.session.delete(drawing)
        db.session.commit()

        return jsonify({'message': 'Drawing deleted successfully'}), 200

    except Exception as e:
        logger.error(f"Error deleting drawing: {str(e)}")
        return jsonify({'error': str(e)}), 500


@learn_by_drawing_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    """
    Get user's learning statistics.

    Returns:
    {
        "total_drawings": 25,
        "topics_explored": 5,
        "average_score": 7.8,
        "total_badges": 3,
        "recent_badges": ["First Drawing", "Water Cycle Expert"]
    }
    """
    try:
        user_id = get_jwt_identity()

        total_drawings = LearningDrawing.get_user_drawings_count(user_id)
        topics_summary = LearningDrawing.get_user_topics_summary(user_id)

        # Get all badges
        all_drawings = LearningDrawing.get_user_drawings(user_id, limit=1000)
        all_badges = set()
        for drawing in all_drawings:
            all_badges.update(drawing.badges_earned or [])

        # Get recent badges (last 5 drawings)
        recent_drawings = LearningDrawing.get_user_drawings(user_id, limit=5)
        recent_badges = []
        for drawing in recent_drawings:
            recent_badges.extend(drawing.badges_earned or [])

        # Calculate average score
        avg_score = sum(t['average_score'] for t in topics_summary) / len(topics_summary) if topics_summary else 0

        return jsonify({
            'total_drawings': total_drawings,
            'topics_explored': len(topics_summary),
            'average_score': round(avg_score, 1),
            'total_badges': len(all_badges),
            'recent_badges': list(set(recent_badges))[:5],
            'topics_summary': topics_summary
        }), 200

    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({'error': str(e)}), 500
