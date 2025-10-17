# app/routes/organi# Register individual tool blueprints (commented out for testing)
from app.routes.stages.organize.collections_routes import collections_bp
from app.routes.stages.organize.tags_routes import tags_bp  
from app.routes.stages.organize.clusters_routes import clusters_bp
from app.routes.stages.organize.concept_graph_routes import concept_graph_bp
from app.routes.stages.organize.saved_views_routes import saved_views_bp

# organize_bp.register_blueprint(collections_bp, url_prefix="/collections")
# organize_bp.register_blueprint(tags_bp, url_prefix="/tags")
# organize_bp.register_blueprint(clusters_bp, url_prefix="/clusters")
# organize_bp.register_blueprint(concept_graph_bp, url_prefix="/concept-graph")
# organize_bp.register_blueprint(saved_views_bp, url_prefix="/saved-views")
import logging
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import BadRequest, NotFound
from app.db import db
from app.models.analysis_results import (
    CollectionsResult, TagTaxonomyResult, DocumentClustersResult, 
    ConceptGraphResult, SavedViewsResult
)
from app.models import UploadedFile, Progress
from datetime import datetime
import uuid

log = logging.getLogger(__name__)

# Create main blueprint
organize_bp = Blueprint('organize', __name__, url_prefix='/api/organize')

# Register individual tool blueprints
# from app.routes.stages.organize.collections_routes import collections_bp
# from app.routes.stages.organize.tags_routes import tags_bp
# from app.routes.stages.organize.clusters_routes import clusters_bp
# from app.routes.stages.organize.concept_graph_routes import concept_graph_bp
# from app.routes.stages.organize.saved_views_routes import saved_views_bp

organize_bp.register_blueprint(collections_bp, url_prefix="/collections")
organize_bp.register_blueprint(tags_bp, url_prefix="/tags")
organize_bp.register_blueprint(clusters_bp, url_prefix="/clusters")
organize_bp.register_blueprint(concept_graph_bp, url_prefix="/concept_graph")
organize_bp.register_blueprint(saved_views_bp, url_prefix="/saved_views")

@organize_bp.before_request
@jwt_required()
def before_request():
    """Ensure user is authenticated for all organize routes."""
    g.current_user_id = get_jwt_identity()
    if not g.current_user_id:
        return jsonify({"error": "Authentication required"}), 401

# ============================================================================
# STAGE-LEVEL ORCHESTRATION ENDPOINTS
# ============================================================================

@organize_bp.route('/start-stage', methods=['POST'])
def start_organize_stage():
    """
    Start the organize stage with multiple tools.
    Body: { 
        "file_ids": ["uuid1", "uuid2", ...], 
        "user_id": "...", 
        "tools": ["collections", "tags", "clusters", "concept-graph", "saved-views"],
        "force": false 
    }
    """
    try:
        data = request.get_json()
        if not data or 'file_ids' not in data:
            return jsonify({"error": "file_ids required"}), 400
        
        file_ids = data.get("file_ids", [])
        tools = data.get("tools", ["collections", "tags", "clusters", "concept-graph", "saved-views"])
        force = bool(data.get("force", False))
        user_id = g.current_user_id
        
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

        # Create progress record for stage orchestration
        prog_id = uuid.uuid4()
        progress = Progress(
            id=prog_id,
            user_id=user_id,
            tool="organize-stage",
            status="in_progress",
            percentage=0
        )
        db.session.add(progress)
        db.session.commit()

        # Define organize stage tools mapping
        organize_tools_map = {
            "collections": "collections_boards",
            "tags": "tag_taxonomy_manager", 
            "clusters": "cluster_builder",
            "concept-graph": "concept_graph",
            "saved-views": "saved_views"
        }
        
        # Start individual tools using the dispatch mechanism
        # from app.tasks.learning_paths_stage_tasks import _dispatch_tool
        
        dispatched_tools = []
        for tool in tools:
            tool_key = organize_tools_map.get(tool)
            if tool_key:
                try:
                    # dispatched = _dispatch_tool(tool_key, file_ids, user_id)
                    # For now, just log that we would dispatch
                    dispatched_tools.append(tool)
                    log.info(f"[Organize Stage] Would dispatch tool: {tool} (key: {tool_key})")
                except Exception as e:
                    log.error(f"[Organize Stage] Error dispatching tool {tool}: {e}")
            else:
                log.warning(f"[Organize Stage] Unknown tool: {tool}")
        
        # Update progress
        progress.percentage = 10
        db.session.commit()
        
        return jsonify({
            "message": "Organize stage started",
            "progress_id": str(prog_id),
            "file_count": len(file_ids),
            "requested_tools": tools,
            "dispatched_tools": dispatched_tools,
            "tools_dispatched": len(dispatched_tools)
        }), 202

    except Exception as e:
        log.error(f"Organize stage start failed: {e}")
        return jsonify({"error": "Failed to start organize stage"}), 500

@organize_bp.route('/results/organize_stage_full', methods=['GET'])
def get_full_organize_results():
    """Get complete organize stage results (all tools combined)."""
    try:
        file_ids_param = request.args.get('file_ids')
        if not file_ids_param:
            raise BadRequest("file_ids parameter required")
        
        file_ids = [uuid.UUID(fid.strip()) for fid in file_ids_param.split(',')]
        user_id = g.current_user_id
        
        # Validate file ownership
        files = db.session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()
        
        if len(files) != len(file_ids):
            raise NotFound("Some files not found or not accessible")
        
        # Get results from all organize tools
        collections = db.session.query(CollectionsResult).filter(
            CollectionsResult.file_id.in_(file_ids),
            CollectionsResult.is_active == True
        ).order_by(CollectionsResult.version.desc()).first()
        
        tags = db.session.query(TagTaxonomyResult).filter(
            TagTaxonomyResult.file_id.in_(file_ids),
            TagTaxonomyResult.is_active == True
        ).order_by(TagTaxonomyResult.version.desc()).first()
        
        clusters = db.session.query(DocumentClustersResult).filter(
            DocumentClustersResult.file_id.in_(file_ids),
            DocumentClustersResult.is_active == True
        ).order_by(DocumentClustersResult.version.desc()).first()
        
        concept_graph = db.session.query(ConceptGraphResult).filter(
            ConceptGraphResult.file_id.in_(file_ids),
            ConceptGraphResult.is_active == True
        ).order_by(ConceptGraphResult.version.desc()).first()
        
        # Get saved views from Progress table
        saved_views_progress = db.session.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.tool == "saved_views_manager",
            Progress.status == "completed",
            Progress.result_data.isnot(None)
        ).order_by(Progress.completed_at.desc()).first()
        
        saved_views_data = None
        saved_views_count = 0
        if saved_views_progress and saved_views_progress.result_data:
            saved_views_data = saved_views_progress.result_data
            default_views = saved_views_data.get('default_views', [])
            contextual_views = saved_views_data.get('contextual_views', [])
            saved_views_count = len(default_views) + len(contextual_views)
        
        # Compile comprehensive results
        result = {
            "stage": "organize",
            "file_count": len(file_ids),
            "completed_tools": 0,
            "total_tools": 5,
            "tools": {
                "collections": {
                    "status": "completed" if collections else "not_found",
                    "total_collections": collections.total_collections if collections else 0,
                    "data": collections.collections if collections else []
                },
                "tags": {
                    "status": "completed" if tags else "not_found", 
                    "total_tags": tags.total_tags if tags else 0,
                    "taxonomy_depth": tags.taxonomy_depth if tags else 0
                },
                "clusters": {
                    "status": "completed" if clusters else "not_found",
                    "total_clusters": clusters.total_clusters if clusters else 0,
                    "algorithm_used": clusters.algorithm_used if clusters else None
                },
                "concept_graph": {
                    "status": "completed" if concept_graph else "not_found",
                    "total_nodes": concept_graph.total_nodes if concept_graph else 0,
                    "total_edges": concept_graph.total_edges if concept_graph else 0
                },
                "saved_views": {
                    "status": "completed" if saved_views_data else "not_found",
                    "total_views": saved_views_count
                }
            },
            "summary": {
                "stage_completion": 0,
                "last_updated": None
            }
        }
        
        # Calculate completion
        completed_count = sum(1 for tool in result["tools"].values() if tool["status"] == "completed")
        result["completed_tools"] = completed_count
        result["summary"]["stage_completion"] = (completed_count / 5) * 100
        
        # Get most recent update time
        latest_times = []
        for res in [collections, tags, clusters, concept_graph]:
            if res and res.updated_at:
                latest_times.append(res.updated_at)
        
        # Add saved views update time
        if saved_views_progress and saved_views_progress.completed_at:
            latest_times.append(saved_views_progress.completed_at)
        
        if latest_times:
            result["summary"]["last_updated"] = max(latest_times).isoformat()
        
        return jsonify(result)
        
    except Exception as e:
        log.error(f"[Full Organize Results API] Error: {e}")
        return jsonify({"error": str(e)}), 500
