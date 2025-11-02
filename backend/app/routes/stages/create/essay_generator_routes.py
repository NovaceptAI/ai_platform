import logging
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest, NotFound
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models.status import Progress
from app.models.files import UploadedFile
from app.services.stages.create.essay_generator_service import EssayGeneratorService
from app.tasks.essay_generator_tasks import generate_essay_task
from datetime import datetime

log = logging.getLogger(__name__)

essay_generator_bp = Blueprint('essay_generator', __name__)

def _get_user_id():
    """Get current user ID from JWT token or request data."""
    try:
        from flask_jwt_extended import get_jwt_identity
        return get_jwt_identity()
    except Exception:
        # Fallback for testing without JWT - try query params first
        return request.args.get("user_id", "test_user")

@essay_generator_bp.route('/start', methods=['POST'])
def start_essay_generation():
    """
    Start essay generation for uploaded files.
    
    Expected JSON:
    {
        "file_ids": [1, 2, 3],
        "options": {
            "essay_type": "analytical",
            "length": "medium",
            "include_citations": true,
            "academic_level": "college",
            "tone": "formal"
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
            "essay_type": "analytical",
            "length": "medium",
            "include_citations": True,
            "academic_level": "college",
            "tone": "formal"
        })
        
        # Get current user
        user_id = _get_user_id()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        log.info(f"[EssayGeneratorRoutes] Starting essay generation for user {user_id}, files: {file_ids}")
        
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
            task_type='essay_generator',
            status='pending',
            current_step='Initializing essay generation',
            progress_percentage=0,
            file_ids=file_ids,
            created_at=datetime.utcnow()
        )
        
        db.session.add(progress)
        db.session.commit()
        
        # Start Celery task
        try:
            task = generate_essay_task.delay(
                user_id=user_id,
                file_ids=file_ids,
                progress_id=str(progress.id),
                options=options
            )
            
            # Update progress with task ID
            progress.task_id = task.id
            db.session.commit()
            
            log.info(f"[EssayGeneratorRoutes] Started essay generation task {task.id}")
            
            return jsonify({
                "message": "Essay generation started",
                "task_id": task.id,
                "progress_id": str(progress.id),
                "status": "started",
                "options": options
            }), 202
            
        except Exception as e:
            log.error(f"[EssayGeneratorRoutes] Failed to start Celery task: {e}")
            
            # Update progress to failed
            progress.status = 'failed'
            progress.error_message = f"Failed to start task: {str(e)}"
            db.session.commit()
            
            return jsonify({
                "error": "Failed to start essay generation",
                "details": str(e)
            }), 500
        
    except Exception as e:
        log.error(f"[EssayGeneratorRoutes] Error in start_essay_generation: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@essay_generator_bp.route('/progress/<progress_id>', methods=['GET'])
def get_essay_generation_progress(progress_id):
    """Get the progress of essay generation."""
    try:
        # Get current user
        user_id = _get_user_id()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        # Get progress record
        progress = db.session.query(Progress).filter(
            Progress.id == progress_id,
            Progress.user_id == user_id,
            Progress.task_type == 'essay_generator'
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
        log.error(f"[EssayGeneratorRoutes] Error getting progress: {e}")
        return jsonify({
            "error": "Failed to get progress",
            "details": str(e)
        }), 500

@essay_generator_bp.route('/results/<progress_id>', methods=['GET'])
def get_essay_generation_results(progress_id):
    """Get the results of completed essay generation."""
    try:
        # Get current user
        user_id = _get_user_id()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        # Get progress record
        progress = db.session.query(Progress).filter(
            Progress.id == progress_id,
            Progress.user_id == user_id,
            Progress.task_type == 'essay_generator'
        ).first()
        
        if not progress:
            return jsonify({"error": "Progress record not found"}), 404
        
        if progress.status != 'completed':
            return jsonify({
                "error": "Essay generation not completed yet",
                "status": progress.status,
                "current_step": progress.current_step,
                "progress_percentage": progress.progress_percentage
            }), 202
        
        if not progress.result_data:
            return jsonify({"error": "No results available"}), 404
        
        # Return the essay generation results
        results = progress.result_data
        
        response_data = {
            "progress_id": str(progress.id),
            "task_id": progress.task_id,
            "status": progress.status,
            "results": results,
            "created_at": progress.created_at.isoformat() if progress.created_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
        }
        
        log.info(f"[EssayGeneratorRoutes] Returning essay generation results for progress {progress_id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        log.error(f"[EssayGeneratorRoutes] Error getting results: {e}")
        return jsonify({
            "error": "Failed to get results",
            "details": str(e)
        }), 500

@essay_generator_bp.route('/info', methods=['GET'])
def get_essay_generator_info():
    """Get information about the essay generator service."""
    try:
        service = EssayGeneratorService()
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
                "start": "POST with file_ids and optional essay options",
                "progress": "GET to check task progress",
                "results": "GET to retrieve completed essays",
                "info": "GET to get service information"
            },
            "essay_options": {
                "essay_type": ["analytical", "argumentative", "comparative", "expository", "research_based"],
                "length": ["short", "medium", "long"],
                "academic_level": ["high_school", "college", "graduate"],
                "tone": ["formal", "semi_formal", "academic"]
            }
        }), 200
        
    except Exception as e:
        log.error(f"[EssayGeneratorRoutes] Error getting service info: {e}")
        return jsonify({
            "error": "Failed to get service info",
            "details": str(e)
        }), 500

@essay_generator_bp.route('/test', methods=['POST'])
def test_essay_generator():
    """Test endpoint for essay generator service."""
    try:
        data = request.get_json() or {}
        
        # Create test file data
        test_file_data = {
            'file_id': 999,
            'file_name': 'test_essay_document.txt',
            'content': data.get('content', 'This is a test document about the importance of critical thinking in education. Critical thinking involves analyzing information, evaluating evidence, and forming reasoned judgments. It is essential for academic success and lifelong learning. Students who develop strong critical thinking skills are better equipped to navigate complex problems and make informed decisions.'),
            'summary': 'Test document about critical thinking in education and its importance for student success',
            'topics': ['critical thinking', 'education', 'student success', 'analytical skills', 'problem solving'],
            'entities': {'concepts': ['critical thinking', 'analysis'], 'domains': ['education', 'learning']},
            'key_points': [
                {'text': 'Critical thinking involves analyzing and evaluating information systematically'},
                {'text': 'Students with strong critical thinking skills perform better academically'},
                {'text': 'Critical thinking is essential for making informed decisions'},
                {'text': 'Educational institutions should prioritize critical thinking development'}
            ]
        }
        
        options = data.get('options', {
            "essay_type": "analytical",
            "length": "medium",
            "include_citations": True,
            "academic_level": "college",
            "tone": "formal"
        })
        
        # Test the service
        service = EssayGeneratorService()
        result = service.generate_essay(test_file_data, options)
        
        return jsonify({
            "message": "Essay generator test completed",
            "test_result": result
        }), 200
        
    except Exception as e:
        log.error(f"[EssayGeneratorRoutes] Error in test: {e}")
        return jsonify({
            "error": "Test failed",
            "details": str(e)
        }), 500

# Error handlers
@essay_generator_bp.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request", "message": str(error)}), 400

@essay_generator_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401

@essay_generator_bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found", "message": str(error)}), 404

@essay_generator_bp.errorhandler(500)
def internal_error(error):
    log.error(f"[EssayGeneratorRoutes] Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500
