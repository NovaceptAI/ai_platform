# app/routes/stages/organize/clusters_routes.py
import logging
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from werkzeug.exceptions import BadRequest, NotFound
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress, UploadedFile
from app.models.analysis_results import DocumentClustersResult
from app.tasks.clustering_tasks import create_content_clusters_task
# from app.services.stages.organize.clusters_service import ClustersService

log = logging.getLogger(__name__)

clusters_bp = Blueprint("clusters", __name__)

def _get_user_id():
    """Get current user ID from JWT token."""
    return get_jwt_identity()

@clusters_bp.route("/start", methods=["POST"])
@jwt_required()
def start_clusters():
    """
    Start document clustering for files.
    Body: {
        "file_ids": ["uuid1", "uuid2", ...],
        "user_id": "...",
        "force": false,
        "cluster_config": {
            "max_clusters": 5,
            "similarity_threshold": 0.3,
            "clustering_method": "semantic",
            "mode": "auto"  // auto | content | document
        }
    }
    """
    try:
        data = request.get_json(force=True)
        file_ids = data.get("file_ids", [])
        force = bool(data.get("force", False))
        cluster_config = data.get("cluster_config", {})
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
            tool="clusters",
            status="in_progress",
            percentage=0
        )
        db.session.add(progress)
        db.session.commit()

        # Start task with configuration
        create_content_clusters_task.apply_async(
            args=[user_id, file_ids, str(prog_id), cluster_config],
            countdown=0
        )

        return jsonify({
            "message": "Document clustering started",
            "progress_id": str(prog_id),
            "file_count": len(file_ids),
            "config": cluster_config
        }), 202

    except Exception as e:
        log.error(f"Clusters start failed: {e}")
        return jsonify({"error": "Failed to start document clustering"}), 500

@clusters_bp.route("/", methods=["POST"])
@jwt_required()
def run_clusters():
    """Execute document clustering tool individually."""
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
                "content": getattr(file, 'content', ''),
                "summary": getattr(file, 'summary', ''),
                "topics": getattr(file, 'topics', []),
                "entities": getattr(file, 'entities', {})
            })
        
        # Start background task
        task = create_content_clusters_task.delay(user_id, file_ids)
        
        log.info(f"[Clusters API] Started task {task.id} for user {user_id}")
        
        return jsonify({
            "message": "Document clustering started",
            "task_id": task.id,
            "status": "processing",
            "file_count": len(file_data),
            "tool": "clusters"
        }), 202
        
    except Exception as e:
        log.error(f"[Clusters API] Error: {e}")
        return jsonify({"error": str(e)}), 500

@clusters_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
@jwt_required()
def clusters_progress(progress_id):
    """Get progress for document clustering."""
    try:
        progress = db.session.query(Progress).filter_by(id=progress_id).first()
        if not progress:
            return jsonify({"error": "Progress not found"}), 404

        return jsonify({
            "progress_id": str(progress.id),
            "status": progress.status,
            "percentage": progress.percentage or 0,
            "tool": "clusters",
            "created_at": progress.created_at.isoformat() if progress.created_at else None,
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None
        })

    except Exception as e:
        log.error(f"Clusters progress fetch failed: {e}")
        return jsonify({"error": "Failed to fetch progress"}), 500

@clusters_bp.route("/results", methods=["GET"])
@jwt_required()
def clusters_results():
    """Get document clustering results."""
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

        # Get clustering results
        results = db.session.query(DocumentClustersResult).filter(
            DocumentClustersResult.file_id.in_(file_ids),
            DocumentClustersResult.is_active == True
        ).order_by(DocumentClustersResult.version.desc()).all()

        formatted_results = []
        for result in results:
            # Extract insights from quality_metrics (which stores the insights dict)
            insights = result.quality_metrics or {}

            # Calculate statistics from clusters for frontend compatibility
            clusters = result.clusters or []
            cluster_sizes = [len(c.get("file_details", c.get("files", []))) for c in clusters]

            # Total documents = number of files uploaded (not pages/items in clusters)
            # This is simply the count of file_ids requested
            total_documents = len(file_ids)

            statistics = {
                "total_documents": total_documents,
                "total_clusters": len(clusters),
                "cluster_size_distribution": {
                    "min": min(cluster_sizes) if cluster_sizes else 0,
                    "max": max(cluster_sizes) if cluster_sizes else 0,
                    "mean": sum(cluster_sizes) / len(cluster_sizes) if cluster_sizes else 0,
                    "median": sorted(cluster_sizes)[len(cluster_sizes) // 2] if cluster_sizes else 0
                }
            }

            formatted_results.append({
                "id": str(result.id),
                "file_id": str(result.file_id),
                "version": result.version,
                "total_clusters": result.total_clusters,
                "algorithm_used": result.algorithm_used,
                "clusters": result.clusters,
                "similarity_data": result.similarity_data,
                "quality_metrics": result.quality_metrics,
                "insights": insights,  # Frontend expects this
                "statistics": statistics,  # Frontend expects this
                "visualization_data": result.visualization_data,
                "created_at": result.created_at.isoformat(),
                "updated_at": result.updated_at.isoformat()
            })

        return jsonify({
            "tool": "clusters",
            "file_count": len(file_ids),
            "results_count": len(formatted_results),
            "results": formatted_results
        })

    except Exception as e:
        log.error(f"Clusters results fetch failed: {e}")
        return jsonify({"error": "Failed to fetch clustering results"}), 500
