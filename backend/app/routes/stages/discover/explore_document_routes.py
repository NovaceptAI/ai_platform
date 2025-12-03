# app/routes/stages/discover/explore_document_routes.py

import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import uuid4
from app.db import db
from app.models import Progress, UploadedFile
from app.tasks.explore_orchestrator_tasks import orchestrate_exploration_task

log = logging.getLogger(__name__)

explore_document_bp = Blueprint("explore_document", __name__)

@explore_document_bp.route("/validate", methods=["POST"])
@jwt_required()
def validate_files_for_exploration():
    """
    Common validation endpoint for all exploration tools.
    Checks which tools have already been run and what data exists.

    Body: { "file_ids": ["uuid1", "uuid2", ...] }
    Returns: {
        "files": [{
            "file_id": "...",
            "file_name": "...",
            "has_summary": bool,
            "has_topics": bool,
            "has_entities": bool,
            "has_relationships": bool,
            "has_evidence": bool,
            "has_segments": bool,
            "missing_tools": ["tool1", "tool2", ...],
            "available_tools": ["tool3", "tool4", ...],
            "all_complete": bool
        }],
        "all_complete": bool,
        "can_proceed": bool,
        "message": "..."
    }
    """
    try:
        from app.models import FilePage, TopicModelResult, DocumentAnalysisResult, SegmentResult, ChronologyResult, SentimentResult

        from uuid import UUID

        data = request.get_json(force=True)
        file_ids_raw = data.get("file_ids", [])
        user_id = get_jwt_identity()

        if not file_ids_raw:
            return jsonify({"error": "file_ids required"}), 400

        # Convert string UUIDs to UUID objects
        try:
            file_ids = [UUID(fid) if isinstance(fid, str) else fid for fid in file_ids_raw]
        except (ValueError, AttributeError) as e:
            return jsonify({"error": f"Invalid file_id format: {str(e)}"}), 400

        log.info(f"[Explore Document Validate] Validating files: {file_ids} for user: {user_id}")

        # Validate file ownership
        files = db.session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()

        log.info(f"[Explore Document Validate] Found {len(files)} files out of {len(file_ids)} requested")

        if len(files) != len(file_ids):
            found_ids = [str(f.id) for f in files]
            missing_ids = [fid for fid in file_ids if fid not in found_ids]
            log.warning(f"[Explore Document Validate] Missing file IDs: {missing_ids}")
            return jsonify({
                "error": "Some files not found or not accessible",
                "requested": file_ids,
                "found": found_ids,
                "missing": missing_ids
            }), 404

        # Check each file for data availability
        file_status = []

        for file in files:
            # Check for summaries in FilePage
            file_pages = db.session.query(FilePage).filter(
                FilePage.file_id == file.id
            ).all()
            has_summary = any(page.page_summary for page in file_pages)

            # Check for topics in TopicModelResult
            topics_data = db.session.query(TopicModelResult).filter(
                TopicModelResult.file_id == file.id
            ).all()
            has_topics = any(topic.topics for topic in topics_data)

            # Check for entities in DocumentAnalysisResult
            doc_analysis = db.session.query(DocumentAnalysisResult).filter(
                DocumentAnalysisResult.file_id == file.id
            ).first()

            has_entities = False

            if doc_analysis and doc_analysis.meta:
                entities = doc_analysis.meta.get('entities_by_type', {})
                has_entities = len(entities) > 0

            # Check for segments in SegmentResult
            segment_data = db.session.query(SegmentResult).filter(
                SegmentResult.file_id == file.id
            ).first()
            has_segments = segment_data and segment_data.segments

            # Check for chronology in ChronologyResult
            chronology_data = db.session.query(ChronologyResult).filter(
                ChronologyResult.file_id == file.id
            ).first()
            has_chronology = chronology_data and chronology_data.events

            # Check for sentiment in SentimentResult
            sentiment_data = db.session.query(SentimentResult).filter(
                SentimentResult.file_id == file.id
            ).first()
            has_sentiment = sentiment_data and sentiment_data.overall_label

            # Determine missing tools
            missing_tools = []
            available_tools = []

            tool_checks = {
                "summary": has_summary,
                "topics": has_topics,
                "chronology": has_chronology,
                "sentiment": has_sentiment,
                "entities": has_entities,
                "segments": has_segments
            }

            for tool, exists in tool_checks.items():
                if exists:
                    available_tools.append(tool)
                else:
                    missing_tools.append(tool)

            file_status.append({
                "file_id": str(file.id),
                "file_name": file.original_file_name,
                "has_summary": has_summary,
                "has_topics": has_topics,
                "has_chronology": has_chronology,
                "has_sentiment": has_sentiment,
                "has_entities": has_entities,
                "has_segments": has_segments,
                "missing_tools": missing_tools,
                "available_tools": available_tools,
                "all_complete": len(missing_tools) == 0
            })

        all_complete = all(f["all_complete"] for f in file_status)
        can_proceed = True  # Can always proceed, orchestrator will skip existing tools

        return jsonify({
            "files": file_status,
            "all_complete": all_complete,
            "can_proceed": can_proceed,
            "message": (
                "All tools have been run on all files" if all_complete
                else "Some tools are missing. The orchestrator will run only the missing tools."
            )
        }), 200

    except Exception as e:
        log.error(f"Validation failed: {e}")
        import traceback
        log.error(traceback.format_exc())
        return jsonify({"error": "Failed to validate files"}), 500


@explore_document_bp.route("/orchestrate", methods=["POST"])
@jwt_required()
def orchestrate_exploration():
    """
    Start async orchestration of document exploration.
    Body: {
        "file_ids": ["uuid1", ...],
        "tools": ["summary", "topics", "entities", "relationships", "evidence", "segments"],
        "force_rerun": false
    }
    Returns: { "progress_id": "uuid", "status": "started", ... }
    """
    try:
        from uuid import UUID

        data = request.get_json(force=True)
        file_ids_raw = data.get("file_ids", [])
        requested_tools = data.get("tools", ["summary", "topics", "entities", "relationships", "evidence", "segments"])
        force_rerun = data.get("force_rerun", False)
        user_id = get_jwt_identity()

        if not file_ids_raw:
            return jsonify({"error": "file_ids required"}), 400

        # Convert string UUIDs to UUID objects
        try:
            file_ids = [UUID(fid) if isinstance(fid, str) else fid for fid in file_ids_raw]
        except (ValueError, AttributeError) as e:
            return jsonify({"error": f"Invalid file_id format: {str(e)}"}), 400

        log.info(f"[Explore Document Orchestrate] Starting orchestration for files: {file_ids}, tools: {requested_tools}")

        # Validate file ownership
        files = db.session.query(UploadedFile).filter(
            UploadedFile.id.in_(file_ids),
            UploadedFile.user_id == user_id
        ).all()

        if len(files) != len(file_ids):
            return jsonify({"error": "Some files not found or not accessible"}), 404

        # Create orchestrator progress record
        prog_id = uuid4()
        progress = Progress(
            id=prog_id,
            user_id=user_id,
            tool="explore_document_orchestrator",
            status="pending",
            percentage=0
        )
        db.session.add(progress)
        db.session.commit()

        # Start orchestrator task
        orchestrate_exploration_task.apply_async(
            args=[user_id, file_ids, requested_tools, str(prog_id), force_rerun],
            countdown=0
        )

        log.info(f"[Explore Document Orchestrator] Started for user {user_id} with {len(file_ids)} files")

        return jsonify({
            "message": "Exploration orchestration started",
            "progress_id": str(prog_id),
            "file_count": len(file_ids),
            "requested_tools": requested_tools
        }), 202

    except Exception as e:
        log.error(f"Orchestration start failed: {e}")
        import traceback
        log.error(traceback.format_exc())
        return jsonify({"error": "Failed to start orchestration"}), 500


@explore_document_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
@jwt_required()
def get_orchestration_progress(progress_id):
    """
    Get progress for orchestration.
    Returns aggregated progress from all tool tasks.

    Returns: {
        "progress_id": "...",
        "status": "running|completed|failed",
        "percentage": 0-100,
        "tools_completed": ["summary", "topics"],
        "tools_running": ["entities"],
        "tools_pending": ["relationships", "evidence", "segments"],
        "tools_skipped": ["segments"],
        "results": { "summary": {...}, "topics": {...} }
    }
    """
    try:
        progress = db.session.query(Progress).filter_by(id=progress_id).first()
        if not progress:
            return jsonify({"error": "Progress not found"}), 404

        result_data = progress.result_data or {}
        tool_progress_ids = result_data.get("tool_progress_ids", {})

        # Aggregate results from individual tool Progress records
        tools_completed = []
        tools_running = []
        tools_pending = []
        tools_skipped = result_data.get("tools_skipped", [])
        aggregated_results = {}

        for tool_name, tool_prog_id in tool_progress_ids.items():
            tool_progress = db.session.query(Progress).filter_by(id=tool_prog_id).first()
            if tool_progress:
                aggregated_results[tool_name] = {
                    "progress_id": str(tool_progress.id),
                    "status": tool_progress.status,
                    "percentage": tool_progress.percentage or 0,
                    "data": tool_progress.result_data if tool_progress.status == "completed" else None
                }

                if tool_progress.status == "completed":
                    tools_completed.append(tool_name)
                elif tool_progress.status in ["running", "in_progress"]:
                    tools_running.append(tool_name)
                else:
                    tools_pending.append(tool_name)

        # Calculate overall percentage
        total_tools = len(tool_progress_ids)
        if total_tools > 0:
            overall_percentage = int((len(tools_completed) / total_tools) * 100)
        else:
            overall_percentage = 100 if progress.status == "completed" else 0

        return jsonify({
            "progress_id": str(progress.id),
            "status": progress.status,
            "percentage": overall_percentage,
            "tools_completed": tools_completed,
            "tools_running": tools_running,
            "tools_pending": tools_pending,
            "tools_skipped": tools_skipped,
            "results": aggregated_results,
            "created_at": progress.created_at.isoformat() if progress.created_at else None,
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None
        }), 200

    except Exception as e:
        log.error(f"Progress fetch failed: {e}")
        import traceback
        log.error(traceback.format_exc())
        return jsonify({"error": "Failed to fetch progress"}), 500
