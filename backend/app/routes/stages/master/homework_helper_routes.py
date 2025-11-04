import logging
from flask import Blueprint, request, jsonify, g
from werkzeug.exceptions import BadRequest, NotFound
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models.status import Progress
from app.models.files import UploadedFile
from app.services.stages.master.homework_helper_service import HomeworkHelperService
from app.tasks.homework_helper_tasks import create_homework_assistance_task
from datetime import datetime
from app.routes.upload import get_current_user_id # keep your existing auth helper
from flask_jwt_extended import jwt_required, get_jwt_identity
log = logging.getLogger(__name__)

homework_helper_bp = Blueprint('homework_helper', __name__)

def _get_user_id():
    """Get current user ID from JWT token or request headers."""
    # Try JWT first
    try:
        user_id = get_jwt_identity()
        if user_id:
            return str(user_id)
    except Exception:
        pass
    
    # Try headers
    user_id = request.headers.get("X-User-Id")
    if user_id:
        return str(user_id)
    
    # Try JSON body
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if user_id:
        return str(user_id)
    
    # Default fallback
    return "admin"

@homework_helper_bp.route('/start', methods=['POST'])
def start_homework_assistance():
    """
    Start homework assistance creation for uploaded files.
    
    Expected JSON:
    {
        "file_ids": [1, 2, 3],
        "options": {
            "include_explanations": true,
            "include_examples": true,
            "include_practice": true,
            "difficulty_level": "medium"
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
            "include_explanations": True,
            "include_examples": True,
            "include_practice": True,
            "difficulty_level": "medium"
        })
        
        # Get current user
        user_id = _get_user_id()
        
        log.info(f"[HomeworkHelperRoutes] Starting homework assistance for user {user_id}, files: {file_ids}")
        
        # Create progress record
        progress_id = uuid4()
        progress = Progress(
            id=progress_id,
            user_id=user_id,
            tool='homework_helper',
            status='in_progress',
            percentage=0
        )
        
        db.session.add(progress)
        db.session.commit()
        
        # Start Celery task
        try:
            task = create_homework_assistance_task.delay(
                user_id=user_id,
                file_ids=file_ids,
                progress_id=str(progress.id),
                options=options
            )
            
            # Update progress with task ID
            progress.task_id = task.id
            db.session.commit()
            
            log.info(f"[HomeworkHelperRoutes] Started homework assistance task {task.id}")
            
            return jsonify({
                "message": "Homework assistance creation started",
                "task_id": task.id,
                "progress_id": str(progress.id),
                "status": "started"
            }), 202
            
        except Exception as e:
            log.error(f"[HomeworkHelperRoutes] Failed to start Celery task: {e}")
            
            # Update progress to failed
            progress.status = 'failed'
            progress.error_message = f"Failed to start task: {str(e)}"
            db.session.commit()
            
            return jsonify({
                "error": "Failed to start homework assistance creation",
                "details": str(e)
            }), 500
        
    except Exception as e:
        log.error(f"[HomeworkHelperRoutes] Error in start_homework_assistance: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@homework_helper_bp.route('/progress/<progress_id>', methods=['GET'])
def get_homework_assistance_progress(progress_id):
    """Get the progress of homework assistance creation."""
    try:
        # Get current user
        user_id = _get_user_id()
        
        # Get progress record
        progress = db.session.query(Progress).filter(
            Progress.id == progress_id,
            Progress.tool == 'homework_helper'
        ).first()
        
        if not progress:
            return jsonify({"error": "Progress record not found"}), 404
        
        response_data = {
            "progress_id": str(progress.id),
            "status": progress.status,
            "percentage": progress.percentage or 0,
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
        log.error(f"[HomeworkHelperRoutes] Error getting progress: {e}")
        return jsonify({
            "error": "Failed to get progress",
            "details": str(e)
        }), 500

@homework_helper_bp.route('/results/<progress_id>', methods=['GET'])
def get_homework_assistance_results(progress_id):
    """Get the results of completed homework assistance creation."""
    try:
        # Get current user
        user_id = _get_user_id()
        
        # Get progress record
        progress = db.session.query(Progress).filter(
            Progress.id == progress_id,
            Progress.tool == 'homework_helper'
        ).first()
        
        if not progress:
            return jsonify({"error": "Progress record not found"}), 404
        
        if progress.status != 'completed':
            return jsonify({
                "error": "Homework assistance creation not completed yet",
                "status": progress.status,
                "percentage": progress.percentage or 0
            }), 202
        
        if not progress.result_data:
            return jsonify({"error": "No results available"}), 404
        
        # Return the homework assistance results
        results = progress.result_data
        
        response_data = {
            "progress_id": str(progress.id),
            "status": progress.status,
            "results": results,
            "created_at": progress.created_at.isoformat() if progress.created_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
        }
        
        log.info(f"[HomeworkHelperRoutes] Returning homework assistance results for progress {progress_id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        log.error(f"[HomeworkHelperRoutes] Error getting results: {e}")
        return jsonify({
            "error": "Failed to get results",
            "details": str(e)
        }), 500

@homework_helper_bp.route('/info', methods=['GET'])
def get_homework_helper_info():
    """Get information about the homework helper service."""
    try:
        service = HomeworkHelperService()
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
                "results": "GET to retrieve completed homework assistance",
                "info": "GET to get service information"
            }
        }), 200
        
    except Exception as e:
        log.error(f"[HomeworkHelperRoutes] Error getting service info: {e}")
        return jsonify({
            "error": "Failed to get service info",
            "details": str(e)
        }), 500

@homework_helper_bp.route('/test', methods=['POST'])
def test_homework_helper():
    """Test endpoint for homework helper service."""
    try:
        data = request.get_json() or {}
        
        # Create test file data
        test_file_data = {
            'file_id': 999,
            'file_name': 'test_document.txt',
            'content': data.get('content', 'This is a test document about mathematics. It covers basic algebra, including solving linear equations and working with variables. Understanding these concepts is fundamental to success in mathematics.'),
            'summary': 'Test document about mathematics fundamentals',
            'topics': ['mathematics', 'algebra', 'linear equations', 'variables'],
            'entities': {'concepts': ['algebra', 'equations'], 'subjects': ['mathematics']},
            'key_points': [
                {'text': 'Linear equations are fundamental in algebra'},
                {'text': 'Variables represent unknown values'},
                {'text': 'Practice is essential for mastery'}
            ]
        }
        
        options = data.get('options', {
            "include_explanations": True,
            "include_examples": True,
            "include_practice": True,
            "difficulty_level": "medium"
        })
        
        # Test the service
        service = HomeworkHelperService()
        result = service.create_homework_assistance(test_file_data, options)
        
        return jsonify({
            "message": "Homework helper test completed",
            "test_result": result
        }), 200
        
    except Exception as e:
        log.error(f"[HomeworkHelperRoutes] Error in test: {e}")
        return jsonify({
            "error": "Test failed",
            "details": str(e)
        }), 500

# Error handlers
@homework_helper_bp.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request", "message": str(error)}), 400

@homework_helper_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401

@homework_helper_bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found", "message": str(error)}), 404

@homework_helper_bp.errorhandler(500)
def internal_error(error):
    log.error(f"[HomeworkHelperRoutes] Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500
