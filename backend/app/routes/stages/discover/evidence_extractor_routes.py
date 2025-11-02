from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress, UploadedFile
from app.models.analysis_results import EvidenceExtractionResult
from app.tasks.evidence_extractor_tasks import build_evidence_for_file

evidence_extractor_bp = Blueprint("evidence_extractor", __name__)

def _get_user_id():
    return get_jwt_identity()

@evidence_extractor_bp.route("/start", methods=["POST"])
@jwt_required()
def start_evidence_extraction():
    """Start evidence extraction for a file"""
    data = request.get_json(force=True)
    file_id = data.get("file_id")
    force = bool(data.get("force", False))
    user_id = _get_user_id()
    
    if not file_id or not user_id:
        return jsonify({"error": "file_id and user_id required"}), 400

    # Ensure pages exist
    exists = db.session.query(FilePage.id).filter_by(file_id=file_id).limit(1).first()
    if not exists:
        return jsonify({"error": "No pages for file_id"}), 404

    # Cache check - return existing results if not forced
    if not force:
        existing = (
            db.session.query(EvidenceExtractionResult)
            .filter_by(file_id=file_id, is_active=True)
            .first()
        )
        if existing:
            return jsonify({
                "message": "Evidence extraction already available",
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
        tool="evidence_extractor",
        status="in_progress",
        percentage=0
    ))
    db.session.commit()

    # Start async task
    build_evidence_for_file.apply_async(
        args=[str(file_id), str(prog_id), force],
        countdown=0
    )
    
    return jsonify({
        "message": "Starting evidence extraction",
        "progress_id": str(prog_id),
        "file_id": str(file_id)
    }), 202

@evidence_extractor_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def evidence_extraction_progress(progress_id):
    """Get progress for evidence extraction task"""
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

@evidence_extractor_bp.route("/results", methods=["GET"])
@jwt_required()
def evidence_extraction_results():
    """Get evidence extraction results for a file"""
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
        db.session.query(EvidenceExtractionResult)
        .filter_by(file_id=file_id, is_active=True)
        .first()
    )
    
    if not result:
        return jsonify({
            "error": "No evidence extraction results found",
            "message": "Run evidence extraction first"
        }), 404

    # Format response
    response_data = {
        "file_id": str(file_id),
        "file_name": uploaded_file.original_file_name,
        "evidence_by_page": result.evidence_by_page or [],
        "aggregated_evidence": result.aggregated_evidence or {},
        "summary": result.summary or {},
        "version": result.version,
        "created_at": result.created_at.isoformat() if result.created_at else None
    }
    
    return jsonify(response_data), 200
