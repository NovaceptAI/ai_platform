# app/routes/stages/organize/saved_views_routes.py
import logging
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import BadRequest, NotFound
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress, UploadedFile
from app.models.analysis_results import SavedViewsResult
from app.tasks.saved_views_tasks import create_saved_views_task
from app.services.stages.organize.saved_views_service import SavedViewsService

log = logging.getLogger(__name__)

saved_views_bp = Blueprint("saved_views", __name__)

def _get_user_id():
    """Get current user ID from JWT token or request data."""
    try:
        return get_jwt_identity()
    except Exception:
        # Fallback for testing without JWT - try query params first
        return request.args.get("user_id", "test_user")

@saved_views_bp.route("/start", methods=["POST"])
def start_saved_views():
    """
    Start saved views generation for files.
    Body: { "file_ids": ["uuid1", "uuid2", ...], "user_id": "...", "force": false }
    """
    try:
        data = request.get_json(force=True)
        file_ids = data.get("file_ids", [])
        force = bool(data.get("force", False))
        user_id = _get_user_id()
        
        if not file_ids or not user_id:
            return jsonify({"error": "file_ids and user_id required"}), 400

        # Validate file ownership
        files = db.session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()
        
        if len(files) != len(file_ids):
            return jsonify({"error": "Some files not found or not accessible"}), 404

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
            tool="saved-views",
            status="in_progress",
            percentage=0
        )
        db.session.add(progress)
        db.session.commit()

        # Start task
        create_saved_views_task.apply_async(args=[user_id, file_ids, str(prog_id)], countdown=0)
        
        return jsonify({
            "message": "Saved views generation started",
            "progress_id": str(prog_id),
            "file_count": len(file_ids)
        }), 202

    except Exception as e:
        log.error(f"Saved views start failed: {e}")
        return jsonify({"error": "Failed to start saved views generation"}), 500

@saved_views_bp.route("/", methods=["POST"])
@jwt_required()
def run_saved_views():
    """Execute saved views tool individually."""
    try:
        data = request.get_json()
        if not data or 'file_ids' not in data:
            raise BadRequest("file_ids required")
        
        file_ids = data['file_ids']
        organization_data = data.get('organization_data', {})
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
                "topics": getattr(file, 'topics', []),
                "entities": getattr(file, 'entities', {}),
                "evidence_items": getattr(file, 'evidence_items', []),
                "created_at": file.created_at.isoformat() if file.created_at else None
            })
        
        # Start background task
        task = create_saved_views_task.delay(user_id, file_ids)
        
        log.info(f"[Saved Views API] Started task {task.id} for user {user_id}")
        
        return jsonify({
            "message": "Saved views creation started",
            "task_id": task.id,
            "status": "processing",
            "file_count": len(file_data),
            "tool": "saved-views"
        }), 202
        
    except Exception as e:
        log.error(f"[Saved Views API] Error: {e}")
        return jsonify({"error": str(e)}), 500

@saved_views_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def saved_views_progress(progress_id):
    """Get progress for saved views generation."""
    try:
        progress = db.session.query(Progress).filter_by(id=progress_id).first()
        if not progress:
            return jsonify({"error": "Progress not found"}), 404

        return jsonify({
            "progress_id": str(progress.id),
            "status": progress.status,
            "percentage": progress.percentage or 0,
            "tool": "saved-views",
            "created_at": progress.created_at.isoformat() if progress.created_at else None,
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None
        })

    except Exception as e:
        log.error(f"Saved views progress fetch failed: {e}")
        return jsonify({"error": "Failed to fetch progress"}), 500

@saved_views_bp.route("/results", methods=["GET"])
def saved_views_results():
    """Get saved views results."""
    try:
        file_ids_param = request.args.get('file_ids')
        if not file_ids_param:
            return jsonify({"error": "file_ids parameter required"}), 400
        
        file_ids = [fid.strip() for fid in file_ids_param.split(',')]
        user_id = _get_user_id()

        # Validate file ownership
        files = db.session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()
        
        if len(files) != len(file_ids):
            return jsonify({"error": "Some files not found or not accessible"}), 404

        # Get saved views results from Progress table (where the task stores them)
        progress_results = db.session.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.tool.in_(["saved-views", "saved_views_manager"]),
            Progress.status == "completed",
            Progress.result_data.isnot(None)
        ).order_by(Progress.completed_at.desc()).all()

        formatted_results = []
        
        # Process each completed saved views task
        for progress in progress_results:
            if progress.result_data and isinstance(progress.result_data, dict):
                result_data = progress.result_data
                
                # Extract view data from the stored result
                default_views = result_data.get('default_views', [])
                contextual_views = result_data.get('contextual_views', [])
                all_views = default_views + contextual_views
                
                formatted_results.append({
                    "id": str(progress.id),
                    "progress_id": str(progress.id),
                    "user_id": user_id,
                    "total_views": result_data.get('total_views', len(all_views)),
                    "default_views_count": len(default_views),
                    "contextual_views_count": len(contextual_views),
                    "views": {
                        "default_views": default_views,
                        "contextual_views": contextual_views
                    },
                    "view_metadata": {
                        "filter_combinations": result_data.get('filter_combinations', {}),
                        "view_templates": result_data.get('view_templates', []),
                        "management_features": result_data.get('management_features', {}),
                        "analytics_framework": result_data.get('analytics_framework', {})
                    },
                    "created_at": progress.created_at.isoformat() if progress.created_at else None,
                    "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
                    "status": progress.status
                })

        return jsonify({
            "tool": "saved-views",
            "file_count": len(file_ids),
            "results_count": len(formatted_results),
            "results": formatted_results
        })

    except Exception as e:
        log.error(f"Saved views results fetch failed: {e}")
        return jsonify({"error": "Failed to fetch saved views results"}), 500
