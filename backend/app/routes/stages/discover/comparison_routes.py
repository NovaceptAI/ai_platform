from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import uuid4
from app.db import db
from app.models import Progress, UploadedFile
from app.models.analysis_results import ComparisonResult
from app.tasks.comparison_tasks import build_comparison_for_files

comparison_bp = Blueprint("comparison", __name__)

def _get_user_id():
    return get_jwt_identity()

@comparison_bp.route("/start", methods=["POST"])
@jwt_required()
def start_comparison():
    """Start comparison analysis for multiple files"""
    data = request.get_json(force=True)
    file_ids = data.get("file_ids", [])
    force = bool(data.get("force", False))
    user_id = _get_user_id()
    
    if not file_ids or len(file_ids) < 2:
        return jsonify({"error": "At least 2 file_ids required for comparison"}), 400

    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    # Verify all files belong to user
    uploaded_files = db.session.query(UploadedFile).filter(
        UploadedFile.id.in_(file_ids),
        UploadedFile.user_id == user_id
    ).all()
    
    if len(uploaded_files) != len(file_ids):
        return jsonify({"error": "Some files not found or don't belong to user"}), 404

    # Create comparison ID and check for existing results
    comparison_key = "_".join(sorted(file_ids))
    
    if not force:
        existing = (
            db.session.query(ComparisonResult)
            .filter_by(comparison_key=comparison_key, is_active=True)
            .first()
        )
        if existing:
            return jsonify({
                "message": "Comparison already available",
                "cached": True,
                "comparison_key": comparison_key,
                "result_id": str(existing.id)
            }), 200

    # Create progress record
    prog_id = uuid4()
    db.session.add(Progress(
        id=prog_id,
        file_id=file_ids[0],  # Use first file as primary
        user_id=user_id,
        tool="comparison",
        status="in_progress",
        percentage=0
    ))
    db.session.commit()

    # Start async comparison task
    build_comparison_for_files.apply_async(
        args=[file_ids, str(prog_id), force],
        countdown=0
    )
    
    return jsonify({
        "message": "Starting document comparison",
        "progress_id": str(prog_id),
        "file_ids": file_ids,
        "comparison_key": comparison_key
    }), 202

@comparison_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def comparison_progress(progress_id):
    """Get progress for comparison task"""
    progress = db.session.query(Progress).get(progress_id)
    if not progress:
        return jsonify({"error": "Progress not found"}), 404
        
    return jsonify({
        "progress_id": str(progress.id),
        "file_id": str(progress.file_id),
        "tool": progress.tool,
        "status": progress.status,
        "percentage": progress.percentage or 0,
        "error_message": progress.error_message
    })

@comparison_bp.route("/results", methods=["GET"])
@jwt_required()
def comparison_results():
    """Get comparison results for files"""
    file_ids = request.args.getlist("file_ids") or request.args.get("file_ids", "").split(",")
    file_ids = [fid.strip() for fid in file_ids if fid.strip()]
    
    if not file_ids or len(file_ids) < 2:
        return jsonify({"error": "At least 2 file_ids required"}), 400
        
    user_id = _get_user_id()
    
    # Verify files belong to user
    uploaded_files = db.session.query(UploadedFile).filter(
        UploadedFile.id.in_(file_ids),
        UploadedFile.user_id == user_id
    ).all()
    
    if len(uploaded_files) != len(file_ids):
        return jsonify({"error": "Some files not found"}), 404

    # Get comparison results
    comparison_key = "_".join(sorted(file_ids))
    result = (
        db.session.query(ComparisonResult)
        .filter_by(comparison_key=comparison_key, is_active=True)
        .first()
    )
    
    if not result:
        return jsonify({
            "error": "No comparison results found",
            "message": "Run comparison analysis first"
        }), 404

    # Create file mapping for response
    file_map = {str(f.id): f.original_file_name for f in uploaded_files}

    # Format response
    response_data = {
        "comparison_key": comparison_key,
        "file_ids": file_ids,
        "file_names": file_map,
        "similarities": result.similarities or {},
        "differences": result.differences or {},
        "relationships": result.relationships or {},
        "synthesis": result.synthesis or {},
        "version": result.version,
        "created_at": result.created_at.isoformat() if result.created_at else None
    }
    
    return jsonify(response_data), 200
