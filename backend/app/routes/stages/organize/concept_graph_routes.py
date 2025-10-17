# app/routes/stages/organize/concept_graph_routes.py
import logging
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import BadRequest, NotFound
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress, UploadedFile
from app.models.analysis_results import ConceptGraphResult
from app.tasks.concept_graph_tasks import build_concept_graph_task
from app.services.stages.organize.concept_graph_service import ConceptGraphService

log = logging.getLogger(__name__)

concept_graph_bp = Blueprint("concept_graph", __name__)

def _get_user_id():
    """Get current user ID from JWT token or request data."""
    try:
        return get_jwt_identity()
    except Exception:
        # Fallback for testing without JWT
        return request.args.get("user_id", "test_user")

@concept_graph_bp.route("/start", methods=["POST"])
def start_concept_graph():
    """
    Start concept graph generation for files.
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
            tool="concept-graph",
            status="in_progress",
            percentage=0
        )
        db.session.add(progress)
        db.session.commit()

        # Start task
        build_concept_graph_task.apply_async(args=[user_id, file_ids, str(prog_id)], countdown=0)
        
        return jsonify({
            "message": "Concept graph generation started",
            "progress_id": str(prog_id),
            "file_count": len(file_ids)
        }), 202

    except Exception as e:
        log.error(f"Concept graph start failed: {e}")
        return jsonify({"error": "Failed to start concept graph generation"}), 500

@concept_graph_bp.route("/", methods=["POST"])
@jwt_required()
def run_concept_graph():
    """Execute concept graph tool individually."""
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
                "relationships": getattr(file, 'relationships', []),
                "summary": getattr(file, 'summary', ''),
                "evidence_items": getattr(file, 'evidence_items', [])
            })
        
        # Start background task
        task = build_concept_graph_task.delay(user_id, file_ids)
        
        log.info(f"[Concept Graph API] Started task {task.id} for user {user_id}")
        
        return jsonify({
            "message": "Concept graph building started",
            "task_id": task.id,
            "status": "processing",
            "file_count": len(file_data),
            "tool": "concept-graph"
        }), 202
        
    except Exception as e:
        log.error(f"[Concept Graph API] Error: {e}")
        return jsonify({"error": str(e)}), 500

@concept_graph_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def concept_graph_progress(progress_id):
    """Get progress for concept graph generation."""
    try:
        progress = db.session.query(Progress).filter_by(id=progress_id).first()
        if not progress:
            return jsonify({"error": "Progress not found"}), 404

        return jsonify({
            "progress_id": str(progress.id),
            "status": progress.status,
            "percentage": progress.percentage or 0,
            "tool": "concept-graph",
            "created_at": progress.created_at.isoformat() if progress.created_at else None,
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None
        })

    except Exception as e:
        log.error(f"Concept graph progress fetch failed: {e}")
        return jsonify({"error": "Failed to fetch progress"}), 500

@concept_graph_bp.route("/results", methods=["GET"])
def concept_graph_results():
    """Get concept graph results."""
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

        # Get concept graph results from Progress table where task results are stored
        progress_results = db.session.query(Progress).filter(
            Progress.tool.in_(['concept-graph', 'concept_graph_builder']),
            Progress.user_id == user_id,
            Progress.status == 'completed',
            Progress.result_data.isnot(None)
        ).order_by(Progress.completed_at.desc()).all()

        formatted_results = []
        for progress in progress_results:
            if progress.result_data:
                result_data = progress.result_data
                
                # Extract graph data from result
                graph_data = result_data.get('graph', {})
                nodes = graph_data.get('nodes', [])
                edges = graph_data.get('edges', [])
                
                formatted_results.append({
                    "id": str(progress.id),
                    "progress_id": str(progress.id),
                    "total_concepts": len(nodes),
                    "total_relationships": len(edges),
                    "nodes": nodes,
                    "edges": edges,
                    "graph_metadata": graph_data.get('metadata', {}),
                    "hierarchies": result_data.get('hierarchies', {}),
                    "analysis": result_data.get('analysis', {}),
                    "interactive_features": result_data.get('interactive_features', {}),
                    "insights": result_data.get('insights', {}),
                    "created_at": progress.created_at.isoformat() if progress.created_at else None,
                    "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
                })

        return jsonify({
            "tool": "concept-graph",
            "file_count": len(file_ids),
            "results_count": len(formatted_results),
            "results": formatted_results
        })

    except Exception as e:
        log.error(f"Concept graph results fetch failed: {e}")
        return jsonify({"error": "Failed to fetch concept graph results"}), 500
