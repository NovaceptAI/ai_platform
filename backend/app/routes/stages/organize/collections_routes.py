# app/routes/stages/organize/collections_routes.py
import logging
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import BadRequest, NotFound
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress, UploadedFile
from app.models.analysis_results import CollectionsResult
from app.tasks.collections_tasks import create_collections_task
from app.services.stages.organize.collections_service import CollectionsService

log = logging.getLogger(__name__)

collections_bp = Blueprint("collections", __name__)

def _get_user_id():
    """Get current user ID from JWT token or request data."""
    try:
        return get_jwt_identity()
    except Exception:
        return request.get_json(force=True).get("user_id", "system")

@collections_bp.route("/start", methods=["POST"])
def start_collections():
    """
    Start collections organization for files.
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
            tool="collections",
            status="in_progress",
            percentage=0
        )
        db.session.add(progress)
        db.session.commit()

        # Start task
        create_collections_task.apply_async(args=[user_id, file_ids, str(prog_id)], countdown=0)
        
        return jsonify({
            "message": "Collections organization started",
            "progress_id": str(prog_id),
            "file_count": len(file_ids)
        }), 202

    except Exception as e:
        log.error(f"Collections start failed: {e}")
        return jsonify({"error": "Failed to start collections organization"}), 500

@collections_bp.route("/", methods=["POST"])
@jwt_required()
def run_collections():
    """Execute collections tool individually."""
    try:
        data = request.get_json()
        if not data or 'file_ids' not in data:
            raise BadRequest("file_ids required")
        
        file_ids = data['file_ids']
        options = data.get('options', {})
        user_id = get_jwt_identity()
        
        # Validate file ownership and prepare data
        files = db.session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()
        
        if len(files) != len(file_ids):
            raise NotFound("Some files not found or not accessible")
        
        # Prepare file data for collections service
        from app.models.analysis_results import TopicModelResult, DocumentAnalysisResult

        file_data = []
        for file in files:
            # Get summary from FilePage
            summary = ""
            pages = db.session.query(FilePage).filter(FilePage.file_id == file.id).all()
            if pages:
                page_summaries = [p.page_summary for p in pages if p.page_summary]
                summary = " ".join(page_summaries) if page_summaries else ""

            # Get topics from TopicModelResult
            topics = []
            topic_result = db.session.query(TopicModelResult).filter(
                TopicModelResult.file_id == file.id,
                TopicModelResult.is_active == True
            ).order_by(TopicModelResult.version.desc()).first()

            if topic_result and topic_result.topics:
                # Extract topic labels from the topics JSONB field
                for topic in topic_result.topics:
                    if isinstance(topic, dict):
                        topic_label = topic.get('label') or topic.get('topic') or topic.get('name')
                        if topic_label:
                            topics.append(topic_label)
                    elif isinstance(topic, str):
                        topics.append(topic)

            # Get entities from DocumentAnalysisResult
            entities = {}
            doc_analysis = db.session.query(DocumentAnalysisResult).filter(
                DocumentAnalysisResult.file_id == file.id,
                DocumentAnalysisResult.is_active == True
            ).order_by(DocumentAnalysisResult.version.desc()).first()

            if doc_analysis:
                # Get entities from meta field
                if doc_analysis.meta and 'entities_by_type' in doc_analysis.meta:
                    entities = doc_analysis.meta.get('entities_by_type', {})

            file_data.append({
                "file_id": str(file.id),
                "file_name": file.original_file_name,
                "file_type": file.file_type,
                "summary": summary,
                "topics": topics,
                "entities": entities,
                "created_at": file.created_at.isoformat() if file.created_at else None
            })
        
        # Start background task
        task = create_collections_task.delay(user_id, file_ids)
        
        log.info(f"[Collections API] Started task {task.id} for user {user_id}")
        
        return jsonify({
            "message": "Collections creation started",
            "task_id": task.id,
            "status": "processing",
            "file_count": len(file_data),
            "tool": "collections"
        }), 202
        
    except Exception as e:
        log.error(f"[Collections API] Error: {e}")
        return jsonify({"error": str(e)}), 500

@collections_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def collections_progress(progress_id):
    """Get progress for collections organization."""
    try:
        progress = db.session.query(Progress).filter_by(id=progress_id).first()
        if not progress:
            return jsonify({"error": "Progress not found"}), 404

        return jsonify({
            "progress_id": str(progress.id),
            "status": progress.status,
            "percentage": progress.percentage or 0,
            "tool": "collections",
            "created_at": progress.created_at.isoformat() if progress.created_at else None,
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None
        })

    except Exception as e:
        log.error(f"Collections progress fetch failed: {e}")
        return jsonify({"error": "Failed to fetch progress"}), 500

@collections_bp.route("/results", methods=["GET"])
def collections_results():
    """Get collections organization results."""
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

        # Get collections results
        results = db.session.query(CollectionsResult).filter(
            CollectionsResult.file_id.in_(file_ids),
            CollectionsResult.is_active == True
        ).order_by(CollectionsResult.version.desc()).all()

        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": str(result.id),
                "file_id": str(result.file_id),
                "version": result.version,
                "total_collections": result.total_collections,
                "collections": result.collections,
                "theme_analysis": result.theme_analysis,
                "organization_insights": result.organization_insights,
                "created_at": result.created_at.isoformat(),
                "updated_at": result.updated_at.isoformat()
            })

        return jsonify({
            "tool": "collections",
            "file_count": len(file_ids),
            "results_count": len(formatted_results),
            "results": formatted_results
        })

    except Exception as e:
        log.error(f"Collections results fetch failed: {e}")
        return jsonify({"error": "Failed to fetch collections results"}), 500
