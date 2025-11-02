import logging
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest, NotFound
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models.status import Progress
from app.models.files import UploadedFile
from app.services.stages.master.visual_study_guide_service import VisualStudyGuideService
from app.tasks.visual_study_guide_tasks import create_visual_study_guide_task
from datetime import datetime

log = logging.getLogger(__name__)

visual_study_guide_bp = Blueprint('visual_study_guide', __name__)

def _get_user_id():
    """Get current user ID from JWT token or request data."""
    try:
        from flask_jwt_extended import get_jwt_identity
        return get_jwt_identity()
    except Exception:
        # Fallback for testing without JWT - try query params first
        return request.args.get("user_id", "test_user")

@visual_study_guide_bp.route('/start', methods=['POST'])
def start_visual_study_guide():
    """
    Start visual study guide creation for uploaded files.
    
    Expected JSON:
    {
        "file_ids": [1, 2, 3],
        "options": {
            "include_concept_maps": true,
            "include_timelines": true,
            "include_diagrams": true,
            "style": "modern"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        file_ids = data.get('file_ids', [])
        if not file_ids:
            return jsonify({"error": "file_ids is required"}), 400
        
        options = data.get('options', {
            "include_concept_maps": True,
            "include_timelines": True,
            "include_diagrams": True,
            "style": "modern"
        })
        
        # Get current user
        user_id = _get_user_id()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        log.info(f"[VisualStudyGuideRoutes] Starting visual study guide for user {user_id}, files: {file_ids}")
        
        # Validate file ownership
        files = db.session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()
        
        if len(files) != len(file_ids):
            return jsonify({"error": "Some files not found or not accessible"}), 404
        
        # Create progress record
        progress = Progress(
            user_id=user_id,
            task_type='visual_study_guide',
            status='pending',
            current_step='Initializing visual study guide creation',
            progress_percentage=0,
            file_ids=file_ids,
            created_at=datetime.utcnow()
        )
        
        db.session.add(progress)
        db.session.commit()
        
        # Start Celery task
        try:
            task = create_visual_study_guide_task.delay(
                user_id=user_id,
                file_ids=file_ids,
                progress_id=str(progress.id),
                options=options
            )
            
            # Update progress with task ID
            progress.task_id = task.id
            db.session.commit()
            
            log.info(f"[VisualStudyGuideRoutes] Started visual study guide task {task.id}")
            
            return jsonify({
                "message": "Visual study guide creation started",
                "task_id": task.id,
                "progress_id": str(progress.id),
                "status": "started"
            }), 202
            
        except Exception as e:
            log.error(f"[VisualStudyGuideRoutes] Failed to start Celery task: {e}")
            
            # Update progress to failed
            progress.status = 'failed'
            progress.error_message = f"Failed to start task: {str(e)}"
            db.session.commit()
            
            return jsonify({
                "error": "Failed to start visual study guide creation",
                "details": str(e)
            }), 500
        
    except Exception as e:
        log.error(f"[VisualStudyGuideRoutes] Error in start_visual_study_guide: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@visual_study_guide_bp.route('/progress/<progress_id>', methods=['GET'])
def get_visual_study_guide_progress(progress_id):
    """Get the progress of visual study guide creation."""
    try:
        # Get current user
        user_id = _get_user_id()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        # Get progress record
        progress = db.session.query(Progress).filter(
            Progress.id == progress_id,
            Progress.user_id == user_id,
            Progress.task_type == 'visual_study_guide'
        ).first()
        
        if not progress:
            return jsonify({"error": "Progress record not found"}), 404
        
        response_data = {
            "progress_id": str(progress.id),
            "task_id": progress.task_id,
            "status": progress.status,
            "current_step": progress.current_step,
            "progress_percentage": progress.progress_percentage,
            "created_at": progress.created_at.isoformat() if progress.created_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
        }
        
        if progress.error_message:
            response_data["error_message"] = progress.error_message
        
        if progress.status == 'completed' and progress.result_data:
            response_data["has_results"] = True
        else:
            response_data["has_results"] = False
        
        return jsonify(response_data), 200
        
    except Exception as e:
        log.error(f"[VisualStudyGuideRoutes] Error getting progress: {e}")
        return jsonify({
            "error": "Failed to get progress",
            "details": str(e)
        }), 500

@visual_study_guide_bp.route('/results/<progress_id>', methods=['GET'])
def get_visual_study_guide_results(progress_id):
    """Get the results of completed visual study guide creation."""
    try:
        # Get current user
        user_id = _get_user_id()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        # Get progress record
        progress = db.session.query(Progress).filter(
            Progress.id == progress_id,
            Progress.user_id == user_id,
            Progress.task_type == 'visual_study_guide'
        ).first()
        
        if not progress:
            return jsonify({"error": "Progress record not found"}), 404
        
        if progress.status != 'completed':
            return jsonify({
                "error": "Visual study guide creation not completed yet",
                "status": progress.status,
                "current_step": progress.current_step,
                "progress_percentage": progress.progress_percentage
            }), 202
        
        if not progress.result_data:
            return jsonify({"error": "No results available"}), 404
        
        # Return the visual study guide results
        results = progress.result_data
        
        response_data = {
            "progress_id": str(progress.id),
            "task_id": progress.task_id,
            "status": progress.status,
            "results": results,
            "created_at": progress.created_at.isoformat() if progress.created_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
        }
        
        log.info(f"[VisualStudyGuideRoutes] Returning visual study guide results for progress {progress_id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        log.error(f"[VisualStudyGuideRoutes] Error getting results: {e}")
        return jsonify({
            "error": "Failed to get results",
            "details": str(e)
        }), 500

@visual_study_guide_bp.route('/info', methods=['GET'])
def get_visual_study_guide_info():
    """Get information about the visual study guide service."""
    try:
        service = VisualStudyGuideService()
        info = service.get_service_info()
        
        return jsonify({
            "service": info,
            "endpoints": {
                "start": "/start",
                "progress": "/progress/<progress_id>",
                "results": "/results/<progress_id>",
                "info": "/info"
            },
            "usage": {
                "start": "POST with file_ids and optional options",
                "progress": "GET to check task progress",
                "results": "GET to retrieve completed visual study guide",
                "info": "GET to get service information"
            }
        }), 200
        
    except Exception as e:
        log.error(f"[VisualStudyGuideRoutes] Error getting service info: {e}")
        return jsonify({
            "error": "Failed to get service info",
            "details": str(e)
        }), 500

@visual_study_guide_bp.route('/test', methods=['POST'])
def test_visual_study_guide():
    """Test endpoint for visual study guide service."""
    try:
        data = request.get_json() or {}
        
        # Create test file data
        test_file_data = {
            'file_id': 999,
            'file_name': 'test_visual_document.txt',
            'content': data.get('content', 'This is a test document about visual learning strategies. It covers concept mapping, mind mapping, diagrams, and visual study techniques. Understanding how to create visual representations helps improve comprehension and retention.'),
            'summary': 'Test document about visual learning and study techniques',
            'topics': ['visual learning', 'concept mapping', 'mind maps', 'diagrams', 'study techniques'],
            'entities': {'techniques': ['mind mapping', 'concept maps'], 'tools': ['diagrams', 'visual aids']},
            'key_points': [
                {'text': 'Visual learning improves comprehension'},
                {'text': 'Concept maps show relationships between ideas'},
                {'text': 'Diagrams simplify complex information'},
                {'text': 'Color coding helps organize information'}
            ]
        }
        
        options = data.get('options', {
            "include_concept_maps": True,
            "include_timelines": True,
            "include_diagrams": True,
            "style": "modern"
        })
        
        # Test the service
        service = VisualStudyGuideService()
        result = service.create_visual_study_guide(test_file_data, options)
        
        return jsonify({
            "message": "Visual study guide test completed",
            "test_result": result
        }), 200
        
    except Exception as e:
        log.error(f"[VisualStudyGuideRoutes] Error in test: {e}")
        return jsonify({
            "error": "Test failed",
            "details": str(e)
        }), 500

# Error handlers
@visual_study_guide_bp.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request", "message": str(error)}), 400

@visual_study_guide_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401

@visual_study_guide_bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found", "message": str(error)}), 404

@visual_study_guide_bp.errorhandler(500)
def internal_error(error):
    log.error(f"[VisualStudyGuideRoutes] Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500
