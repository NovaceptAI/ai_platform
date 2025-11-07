import logging
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import BadRequest, NotFound
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress, UploadedFile
from app.tasks.flashcards_tasks import create_flashcards_task
from app.services.stages.master.flashcards_service import FlashcardsService

log = logging.getLogger(__name__)

flashcards_bp = Blueprint("flashcards", __name__)

def _get_user_id():
    """Get current user ID from JWT token or request data."""
    try:
        return get_jwt_identity()
    except Exception:
        # Fallback for testing without JWT - try query params first
        return request.args.get("user_id", "test_user")

@flashcards_bp.route("/start", methods=["POST"])
@jwt_required()
def start_flashcards():
    """
    Start flashcards generation for files.
    Body: { "file_ids": ["uuid1", "uuid2", ...], "options": {...} }
    """
    try:
        data = request.get_json(force=True)
        file_ids = data.get("file_ids", [])
        options = data.get("options", {})
        user_id = get_jwt_identity()
        
        if not file_ids:
            return jsonify({"error": "file_ids required"}), 400

        # Validate file ownership
        files = db.session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()
        
        found_ids = [str(f.id) for f in files]
        missing_ids = [fid for fid in file_ids if fid not in found_ids]
        
        if missing_ids:
            log.warning(f"Files not found for user {user_id}: {missing_ids}")
            return jsonify({
                "error": "Some files not found or not accessible",
                "missing_file_ids": missing_ids,
                "found_count": len(files),
                "requested_count": len(file_ids)
            }), 404

        # Prepare file data
        file_data = []
        for file in files:
            file_data.append({
                "file_id": str(file.id),
                "file_name": file.original_file_name,
                "file_type": file.file_type,
                "created_at": file.created_at.isoformat() if file.created_at else None
            })

        # Create progress record
        prog_id = uuid4()
        progress = Progress(
            id=prog_id,
            user_id=user_id,
            tool="flashcards",
            status="in_progress",
            percentage=0
        )
        db.session.add(progress)
        db.session.commit()

        # Start task with options
        create_flashcards_task.apply_async(
            args=[user_id, file_ids, str(prog_id)],
            kwargs={'options': options},
            countdown=0
        )
        
        return jsonify({
            "message": "Flashcards generation started",
            "progress_id": str(prog_id),
            "file_count": len(file_ids)
        }), 202

    except Exception as e:
        log.error(f"Flashcards start failed: {e}")
        return jsonify({"error": "Failed to start flashcards generation"}), 500

@flashcards_bp.route("/", methods=["POST"])
@jwt_required()
def run_flashcards():
    """Execute flashcards tool individually."""
    try:
        data = request.get_json()
        if not data or 'file_ids' not in data:
            raise BadRequest("file_ids required")
        
        file_ids = data['file_ids']
        options = data.get('options', {})
        user_id = get_jwt_identity()
        
        # Validate and prepare file data
        files = db.session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()
        
        if len(files) != len(file_ids):
            raise NotFound("Some files not found or not accessible")
        
        file_data = []
        for file in files:
            file_data.append({
                "file_id": str(file.id),
                "file_name": file.original_file_name,
                "file_type": file.file_type,
                "created_at": file.created_at.isoformat() if file.created_at else None
            })
        
        # Start background task
        task = create_flashcards_task.delay(user_id, file_ids)
        
        log.info(f"[Flashcards API] Started task {task.id} for user {user_id}")
        
        return jsonify({
            "message": "Flashcards creation started",
            "task_id": task.id,
            "status": "processing",
            "file_count": len(file_data),
            "tool": "flashcards"
        }), 202
        
    except Exception as e:
        log.error(f"[Flashcards API] Error: {e}")
        return jsonify({"error": str(e)}), 500

@flashcards_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def flashcards_progress(progress_id):
    """Get progress for flashcards generation."""
    try:
        progress = db.session.query(Progress).filter_by(id=progress_id).first()
        if not progress:
            return jsonify({"error": "Progress not found"}), 404

        return jsonify({
            "progress_id": str(progress.id),
            "status": progress.status,
            "percentage": progress.percentage or 0,
            "tool": "flashcards",
            "created_at": progress.created_at.isoformat() if progress.created_at else None,
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None
        })

    except Exception as e:
        log.error(f"Flashcards progress fetch failed: {e}")
        return jsonify({"error": "Failed to fetch progress"}), 500

@flashcards_bp.route("/results", methods=["GET"])
@jwt_required()
def flashcards_results():
    """Get flashcards results."""
    try:
        file_ids_param = request.args.get('file_ids')
        if not file_ids_param:
            return jsonify({"error": "file_ids parameter required"}), 400
        
        file_ids = [fid.strip() for fid in file_ids_param.split(',')]
        user_id = get_jwt_identity()

        # Validate file ownership
        files = db.session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()
        
        found_ids = [str(f.id) for f in files]
        missing_ids = [fid for fid in file_ids if fid not in found_ids]
        
        if missing_ids:
            log.warning(f"Files not found for user {user_id} in results: {missing_ids}")
            return jsonify({
                "error": "Some files not found or not accessible",
                "missing_file_ids": missing_ids,
                "found_count": len(files),
                "requested_count": len(file_ids)
            }), 404

        # Get flashcards results from Progress table where task results are stored
        progress_results = db.session.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.tool == "flashcards",
            Progress.status == "completed",
            Progress.result_data.isnot(None)
        ).order_by(Progress.completed_at.desc()).all()

        formatted_results = []
        for progress in progress_results:
            if progress.result_data:
                result_data = progress.result_data
                
                formatted_results.append({
                    "id": str(progress.id),
                    "progress_id": str(progress.id),
                    "total_cards": result_data.get('total_cards', 0),
                    "files_processed": result_data.get('files_processed', 0),
                    "flashcards": result_data.get('flashcards', []),
                    "files_data": result_data.get('files_data', []),
                    "created_at": progress.created_at.isoformat() if progress.created_at else None,
                    "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
                })

        return jsonify({
            "tool": "flashcards",
            "file_count": len(file_ids),
            "results_count": len(formatted_results),
            "results": formatted_results
        })

    except Exception as e:
        log.error(f"Flashcards results fetch failed: {e}")
        return jsonify({"error": "Failed to fetch flashcards results"}), 500
