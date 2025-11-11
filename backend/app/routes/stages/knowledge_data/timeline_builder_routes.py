"""
Timeline Builder API Routes

Handles HTTP endpoints for timeline creation, management, and visualization.
"""

import logging
import uuid
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.db import db
from app.models.historical_timelines import HistoricalTimeline
from app.services.timeline_storage_service import delete_timeline_from_azure
from app.tasks.timeline_builder_tasks import (
    generate_timeline_from_text_task,
    generate_timeline_from_document_task,
    export_timeline_task,
    enhance_existing_timeline_task
)

logger = logging.getLogger(__name__)

timeline_builder_bp = Blueprint('timeline_builder', __name__)


@timeline_builder_bp.route('/create', methods=['POST'])
def create_timeline():
    """
    Create new timeline from text or document.

    Request body:
        {
            "input_type": "text|document",
            "input_text": "...",  # For text input
            "document": file,     # For document upload
            "category": "history|science|personal|project",
            "time_period": "Ancient Rome",
            "enhance": true
        }

    Returns:
        {
            "success": true,
            "timeline_id": "uuid",
            "message": "Timeline creation started"
        }
    """
    try:
        user_id = request.headers.get('X-User-ID', 'default_user')

        input_type = request.form.get('input_type', 'text')
        category = request.form.get('category')
        time_period = request.form.get('time_period')
        enhance = request.form.get('enhance', 'true').lower() == 'true'

        # Create timeline record
        timeline_id = str(uuid.uuid4())
        azure_folder = f"{user_id}/timelines/{timeline_id}"

        timeline = HistoricalTimeline(
            id=timeline_id,
            user_id=user_id,
            title="Processing...",
            input_type=input_type,
            category=category,
            time_period=time_period,
            azure_folder_path=azure_folder
        )

        if input_type == 'text':
            # Text input
            input_text = request.form.get('input_text')

            if not input_text or len(input_text.strip()) < 50:
                return jsonify({
                    'success': False,
                    'error': 'Input text must be at least 50 characters'
                }), 400

            timeline.input_text = input_text

            db.session.add(timeline)
            db.session.commit()

            # Start async task
            generate_timeline_from_text_task.delay(
                user_id=user_id,
                timeline_id=timeline_id,
                input_text=input_text,
                category=category,
                time_period=time_period,
                enhance=enhance
            )

            logger.info(f"[TimelineRoutes] Created timeline {timeline_id} from text")

            return jsonify({
                'success': True,
                'timeline_id': timeline_id,
                'message': 'Timeline creation started',
                'estimated_time': '30-60 seconds'
            }), 201

        elif input_type == 'document':
            # Document upload
            if 'document' not in request.files:
                return jsonify({
                    'success': False,
                    'error': 'No document provided'
                }), 400

            document = request.files['document']

            if document.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'No document selected'
                }), 400

            # Validate file type
            allowed_extensions = {'.pdf', '.txt', '.docx', '.doc'}
            filename = secure_filename(document.filename)
            file_ext = filename.lower()[filename.rfind('.'):]

            if file_ext not in allowed_extensions:
                return jsonify({
                    'success': False,
                    'error': f'Unsupported file type: {file_ext}. Allowed: PDF, TXT, DOCX, DOC'
                }), 400

            # Read document bytes
            document_bytes = document.read()

            if len(document_bytes) > 10 * 1024 * 1024:  # 10MB limit
                return jsonify({
                    'success': False,
                    'error': 'Document too large (max 10MB)'
                }), 400

            db.session.add(timeline)
            db.session.commit()

            # Start async task
            generate_timeline_from_document_task.delay(
                user_id=user_id,
                timeline_id=timeline_id,
                document_bytes=document_bytes,
                filename=filename,
                category=category,
                time_period=time_period,
                enhance=enhance
            )

            logger.info(f"[TimelineRoutes] Created timeline {timeline_id} from document")

            return jsonify({
                'success': True,
                'timeline_id': timeline_id,
                'message': 'Timeline creation started',
                'estimated_time': '60-90 seconds'
            }), 201

        else:
            return jsonify({
                'success': False,
                'error': f'Invalid input type: {input_type}'
            }), 400

    except Exception as e:
        logger.error(f"[TimelineRoutes] Error creating timeline: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@timeline_builder_bp.route('/timelines', methods=['GET'])
def get_user_timelines():
    """
    Get all timelines for current user.

    Query params:
        limit: Max number of timelines (default 50)
        category: Filter by category

    Returns:
        {
            "success": true,
            "timelines": [...],
            "total_count": 42
        }
    """
    try:
        user_id = request.headers.get('X-User-ID', 'default_user')
        limit = int(request.args.get('limit', 50))
        category = request.args.get('category')

        query = HistoricalTimeline.query.filter_by(user_id=user_id)

        if category:
            query = query.filter_by(category=category)

        timelines = query.order_by(HistoricalTimeline.created_at.desc())\
            .limit(limit)\
            .all()

        total_count = HistoricalTimeline.get_user_timelines_count(user_id)

        return jsonify({
            'success': True,
            'timelines': [t.to_dict() for t in timelines],
            'total_count': total_count
        }), 200

    except Exception as e:
        logger.error(f"[TimelineRoutes] Error getting timelines: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@timeline_builder_bp.route('/timeline/<timeline_id>', methods=['GET'])
def get_timeline(timeline_id):
    """
    Get specific timeline by ID.

    Returns:
        {
            "success": true,
            "timeline": {...}
        }
    """
    try:
        user_id = request.headers.get('X-User-ID', 'default_user')

        timeline = HistoricalTimeline.get_timeline_by_id(timeline_id, user_id)

        if not timeline:
            return jsonify({
                'success': False,
                'error': 'Timeline not found'
            }), 404

        return jsonify({
            'success': True,
            'timeline': timeline.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"[TimelineRoutes] Error getting timeline: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@timeline_builder_bp.route('/timeline/<timeline_id>', methods=['PUT'])
def update_timeline(timeline_id):
    """
    Update timeline metadata.

    Request body:
        {
            "title": "New Title",
            "description": "New description",
            "is_favorite": true,
            "tags": ["tag1", "tag2"],
            "visualization_type": "linear",
            "color_scheme": "historical"
        }

    Returns:
        {
            "success": true,
            "timeline": {...}
        }
    """
    try:
        user_id = request.headers.get('X-User-ID', 'default_user')
        data = request.get_json()

        timeline = HistoricalTimeline.get_timeline_by_id(timeline_id, user_id)

        if not timeline:
            return jsonify({
                'success': False,
                'error': 'Timeline not found'
            }), 404

        # Update allowed fields
        if 'title' in data:
            timeline.title = data['title']
        if 'description' in data:
            timeline.description = data['description']
        if 'is_favorite' in data:
            timeline.is_favorite = data['is_favorite']
        if 'tags' in data:
            timeline.tags = data['tags']
        if 'visualization_type' in data:
            timeline.visualization_type = data['visualization_type']
        if 'color_scheme' in data:
            timeline.color_scheme = data['color_scheme']
        if 'display_options' in data:
            timeline.display_options = data['display_options']

        db.session.commit()

        logger.info(f"[TimelineRoutes] Updated timeline {timeline_id}")

        return jsonify({
            'success': True,
            'timeline': timeline.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"[TimelineRoutes] Error updating timeline: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@timeline_builder_bp.route('/timeline/<timeline_id>', methods=['DELETE'])
def delete_timeline(timeline_id):
    """
    Delete timeline.

    Returns:
        {
            "success": true,
            "message": "Timeline deleted"
        }
    """
    try:
        user_id = request.headers.get('X-User-ID', 'default_user')

        timeline = HistoricalTimeline.get_timeline_by_id(timeline_id, user_id)

        if not timeline:
            return jsonify({
                'success': False,
                'error': 'Timeline not found'
            }), 404

        # Delete from Azure
        if timeline.azure_folder_path:
            delete_timeline_from_azure(timeline.azure_folder_path)

        # Delete from database
        db.session.delete(timeline)
        db.session.commit()

        logger.info(f"[TimelineRoutes] Deleted timeline {timeline_id}")

        return jsonify({
            'success': True,
            'message': 'Timeline deleted'
        }), 200

    except Exception as e:
        logger.error(f"[TimelineRoutes] Error deleting timeline: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@timeline_builder_bp.route('/timeline/<timeline_id>/export', methods=['POST'])
def export_timeline(timeline_id):
    """
    Export timeline to various formats.

    Request body:
        {
            "format": "json|csv|pdf"
        }

    Returns:
        {
            "success": true,
            "export_url": "...",
            "format": "json"
        }
    """
    try:
        user_id = request.headers.get('X-User-ID', 'default_user')
        data = request.get_json() or {}

        export_format = data.get('format', 'json')

        timeline = HistoricalTimeline.get_timeline_by_id(timeline_id, user_id)

        if not timeline:
            return jsonify({
                'success': False,
                'error': 'Timeline not found'
            }), 404

        # Start async export
        task = export_timeline_task.delay(
            user_id=user_id,
            timeline_id=timeline_id,
            export_format=export_format
        )

        logger.info(f"[TimelineRoutes] Started export for timeline {timeline_id}")

        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Export started',
            'format': export_format
        }), 202

    except Exception as e:
        logger.error(f"[TimelineRoutes] Error exporting timeline: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@timeline_builder_bp.route('/timeline/<timeline_id>/enhance', methods=['POST'])
def enhance_timeline(timeline_id):
    """
    Enhance existing timeline with additional research.

    Returns:
        {
            "success": true,
            "task_id": "...",
            "message": "Enhancement started"
        }
    """
    try:
        user_id = request.headers.get('X-User-ID', 'default_user')

        timeline = HistoricalTimeline.get_timeline_by_id(timeline_id, user_id)

        if not timeline:
            return jsonify({
                'success': False,
                'error': 'Timeline not found'
            }), 404

        # Start async enhancement
        task = enhance_existing_timeline_task.delay(
            user_id=user_id,
            timeline_id=timeline_id
        )

        logger.info(f"[TimelineRoutes] Started enhancement for timeline {timeline_id}")

        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Enhancement started',
            'estimated_time': '30-45 seconds'
        }), 202

    except Exception as e:
        logger.error(f"[TimelineRoutes] Error enhancing timeline: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@timeline_builder_bp.route('/categories', methods=['GET'])
def get_categories():
    """
    Get available timeline categories.

    Returns:
        {
            "success": true,
            "categories": [...]
        }
    """
    categories = [
        {'value': 'history', 'label': 'Historical Events', 'icon': 'scroll'},
        {'value': 'science', 'label': 'Scientific Progress', 'icon': 'atom'},
        {'value': 'personal', 'label': 'Personal Timeline', 'icon': 'user'},
        {'value': 'project', 'label': 'Project Timeline', 'icon': 'briefcase'},
        {'value': 'literature', 'label': 'Literary Timeline', 'icon': 'book'},
        {'value': 'art', 'label': 'Art History', 'icon': 'palette'},
        {'value': 'technology', 'label': 'Tech Evolution', 'icon': 'cpu'},
        {'value': 'other', 'label': 'Other', 'icon': 'more-horizontal'}
    ]

    return jsonify({
        'success': True,
        'categories': categories
    }), 200
