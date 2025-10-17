# app/routes/stages/organize/tags_routes.py
import logging
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import BadRequest, NotFound
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress, UploadedFile
from app.models.analysis_results import TagTaxonomyResult
from app.tasks.tagging_tasks import build_tag_taxonomy_task
# from app.services.stages.organize.tagging_service import TaggingService

log = logging.getLogger(__name__)

tags_bp = Blueprint("tags", __name__)

def _get_user_id():
    """Get current user ID from JWT token or request data."""
    try:
        return get_jwt_identity()
    except Exception:
        return request.get_json(force=True).get("user_id", "system")

@tags_bp.route("/start", methods=["POST"])
def start_tags():
    """
    Start tag taxonomy building for files.
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
            tool="tags",
            status="in_progress",
            percentage=0
        )
        db.session.add(progress)
        db.session.commit()

        # Start task
        build_tag_taxonomy_task.apply_async(args=[user_id, file_ids, str(prog_id)], countdown=0)
        
        return jsonify({
            "message": "Tag taxonomy building started",
            "progress_id": str(prog_id),
            "file_count": len(file_ids)
        }), 202

    except Exception as e:
        log.error(f"Tags start failed: {e}")
        return jsonify({"error": "Failed to start tag taxonomy building"}), 500

@tags_bp.route("/", methods=["POST"])
@jwt_required()
def run_tags():
    """Execute tag taxonomy tool individually."""
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
                "topics": getattr(file, 'topics', []),
                "entities": getattr(file, 'entities', {}),
                "keywords": getattr(file, 'keywords', []),
                "summary": getattr(file, 'summary', '')
            })
        
        # Start background task
        task = build_tag_taxonomy_task.delay(user_id, file_ids)
        
        log.info(f"[Tags API] Started task {task.id} for user {user_id}")
        
        return jsonify({
            "message": "Tag taxonomy building started",
            "task_id": task.id,
            "status": "processing",
            "file_count": len(file_data),
            "tool": "tags"
        }), 202
        
    except Exception as e:
        log.error(f"[Tags API] Error: {e}")
        return jsonify({"error": str(e)}), 500

@tags_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def tags_progress(progress_id):
    """Get progress for tag taxonomy building."""
    try:
        progress = db.session.query(Progress).filter_by(id=progress_id).first()
        if not progress:
            return jsonify({"error": "Progress not found"}), 404

        return jsonify({
            "progress_id": str(progress.id),
            "status": progress.status,
            "percentage": progress.percentage or 0,
            "tool": "tags",
            "created_at": progress.created_at.isoformat() if progress.created_at else None,
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None
        })

    except Exception as e:
        log.error(f"Tags progress fetch failed: {e}")
        return jsonify({"error": "Failed to fetch progress"}), 500

@tags_bp.route("/results", methods=["GET"])
def tags_results():
    """Get tag taxonomy results."""
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

        # Get tag taxonomy results
        results = db.session.query(TagTaxonomyResult).filter(
            TagTaxonomyResult.file_id.in_(file_ids),
            TagTaxonomyResult.is_active == True
        ).order_by(TagTaxonomyResult.version.desc()).all()

        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": str(result.id),
                "file_id": str(result.file_id),
                "version": result.version,
                "total_tags": result.total_tags,
                "taxonomy_depth": result.taxonomy_depth,
                "tags": result.tags,
                "hierarchy": result.hierarchy,
                "relationships": result.relationships,
                "tagging_rules": result.tagging_rules,
                "file_tag_assignments": result.file_tag_assignments,
                "created_at": result.created_at.isoformat(),
                "updated_at": result.updated_at.isoformat()
            })

        return jsonify({
            "tool": "tags",
            "file_count": len(file_ids),
            "results_count": len(formatted_results),
            "results": formatted_results
        })

    except Exception as e:
        log.error(f"Tags results fetch failed: {e}")
        return jsonify({"error": "Failed to fetch tag taxonomy results"}), 500
