# app/routes/stages/discover/readability_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress, UploadedFile
from app.models.readability_results import ReadabilityAnalysisResult
from app.tasks.readability_tasks import analyze_readability_for_file

readability_bp = Blueprint("readability", __name__)

def _get_user_id():
    return get_jwt_identity()

@readability_bp.route("/start", methods=["POST"])
@jwt_required()
def start_readability_analysis():
    """Start readability analysis for a file"""
    import logging
    log = logging.getLogger(__name__)

    data = request.get_json(force=True)
    file_id = data.get("file_id")
    force = bool(data.get("force", False))
    user_id = _get_user_id()

    log.info(f"[ReadabilityAnalysis] Start request - file_id: {file_id}, user_id: {user_id}, force: {force}")

    if not file_id or not user_id:
        log.error(f"[ReadabilityAnalysis] Missing required params - file_id: {file_id}, user_id: {user_id}")
        return jsonify({"error": "file_id and user_id required"}), 400

    # Ensure pages exist
    exists = db.session.query(FilePage.id).filter_by(file_id=file_id).limit(1).first()
    if not exists:
        return jsonify({"error": "No pages for file_id. Upload and process the file first."}), 404

    # Cache check - return existing results if not forced
    if not force:
        existing = (
            db.session.query(ReadabilityAnalysisResult)
            .filter_by(file_id=file_id, is_active=True)
            .first()
        )
        if existing:
            return jsonify({
                "message": "Readability analysis already available",
                "cached": True,
                "file_id": str(file_id),
                "result_id": str(existing.id)
            }), 200

    # Create progress record
    prog_id = uuid4()
    db.session.add(Progress(
        id=prog_id,
        file_id=file_id,
        user_id=user_id,
        tool="readability_analyzer",
        status="in_progress",
        percentage=0
    ))
    db.session.commit()

    # Start async task
    analyze_readability_for_file.apply_async(
        args=[str(file_id), str(prog_id), force],
        countdown=0
    )

    return jsonify({
        "message": "Starting readability analysis",
        "progress_id": str(prog_id),
        "file_id": str(file_id)
    }), 202

@readability_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def readability_analysis_progress(progress_id):
    """Get progress for readability analysis task"""
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

@readability_bp.route("/results", methods=["GET"])
@jwt_required()
def readability_analysis_results():
    """Get readability analysis results for a file"""
    file_id = request.args.get("file_id")
    if not file_id:
        return jsonify({"error": "file_id required"}), 400

    user_id = _get_user_id()

    # Verify file belongs to user
    uploaded_file = db.session.query(UploadedFile).filter(
        UploadedFile.id == file_id,
        UploadedFile.user_id == user_id
    ).first()

    if not uploaded_file:
        return jsonify({"error": "File not found"}), 404

    # Get persisted results
    result = (
        db.session.query(ReadabilityAnalysisResult)
        .filter_by(file_id=file_id, is_active=True)
        .first()
    )

    if not result:
        return jsonify({
            "error": "No readability analysis results found",
            "message": "Run readability analysis first"
        }), 404

    # Format response
    response_data = {
        "file_id": str(file_id),
        "file_name": uploaded_file.original_file_name,
        "doc_metrics": result.doc_metrics or {},
        "per_page_analysis": result.per_page_analysis or [],
        "style_analysis": result.style_analysis or {},
        "readability_scores": result.readability_scores or {},
        "issues": result.issues or [],
        "recommendations": result.recommendations or [],
        "summary": result.summary,
        "target_audience": result.target_audience,
        "version": result.version,
        "created_at": result.created_at.isoformat() if result.created_at else None
    }

    return jsonify(response_data), 200
