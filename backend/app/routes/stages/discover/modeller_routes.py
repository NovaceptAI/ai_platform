# app/stages/discover/topic_modeller/routes.py
from flask import Blueprint, request, jsonify, current_app
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.models.analysis_results import TopicModelResult
from app.tasks.topic_modeller_tasks import build_topics_for_file  # NEW import after split
from app.routes.upload import get_current_user_id  # keep your existing auth helper
from flask_jwt_extended import jwt_required, get_jwt_identity

modeller_bp = Blueprint('modeller', __name__)

@modeller_bp.route('/topics/start', methods=['POST'])
@jwt_required()
def start_topics():
    """
    Starts topic extraction for a file_id using page_text from file_pages.
    Creates a Progress row (tool='topics') and dispatches Celery task.
    Body: { "file_id": "...", "force": false }
    """
    try:
        data = request.get_json(force=True)
        file_id = data.get("file_id")
        force = bool(data.get("force", False))
        user_id = get_current_user_id()

        if not file_id:
            return jsonify({"error": "file_id is required"}), 400

        # quick existence check for pages (avoid empty jobs)
        exists = db.session.query(FilePage.id).filter(FilePage.file_id == file_id).limit(1).first()
        if not exists:
            return jsonify({"error": "No pages found for file_id"}), 404

        # CACHE CHECK → return persisted TopicModelResult if present and not forced
        if not force:
            existing = (
                db.session.query(TopicModelResult)
                .filter_by(file_id=file_id, is_active=True)
                .first()
            )
            if existing:
                return jsonify({
                    "message": "Topics already available",
                    "cached": True,
                    "file_id": str(file_id),
                    "result_id": str(existing.id),
                    "num_topics": existing.num_topics,
                }), 200

        # create progress & dispatch
        prog_id = uuid4()
        prog = Progress(
            id=prog_id,
            file_id=file_id,
            user_id=user_id,
            tool="topics",
            status="in_progress",
            percentage=0,
        )
        db.session.add(prog)
        db.session.commit()

        build_topics_for_file.apply_async(args=[str(file_id), str(prog_id), force], countdown=0)

        return jsonify({
            "message": "Processing topics",
            "progress_id": str(prog_id),
            "file_id": str(file_id)
        }), 202

    except Exception as e:
        current_app.logger.exception("/topics/start failed")
        return jsonify({"error": "Failed to start topic extraction"}), 500


@modeller_bp.route('/topics/progress/<uuid:progress_id>', methods=['GET'])
def topics_progress(progress_id):
    p = db.session.query(Progress).get(progress_id)
    if not p:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "progress_id": str(p.id),
        "file_id": str(p.file_id),
        "tool": p.tool,
        "status": p.status,
        "percentage": p.percentage or 0,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None
    })


@modeller_bp.route('/topics/results', methods=['GET'])
def topics_results():
    """
    Returns aggregated topics + per-page topics.
    Query: ?file_id=...
    Prefers persisted TopicModelResult; falls back to scanning FilePage.page_topics.
    """
    file_id = request.args.get("file_id")
    if not file_id:
        return jsonify({"error": "file_id is required"}), 400

    # 1) prefer persisted
    existing = (
        db.session.query(TopicModelResult)
        .filter_by(file_id=file_id, is_active=True)
        .first()
    )
    if existing:
        return jsonify({
            "file_id": str(file_id),
            "topics": existing.topics or [],
            "per_page": [{"page": int(k), "topics": v} for k, v in (existing.page_topics or {}).items()],
            "num_topics": existing.num_topics,
            "coherence": existing.coherence,
            "version": existing.version,
        })

    # 2) fallback to page scan
    pages = (
        db.session.query(FilePage.page_number, FilePage.page_topics)
        .filter(FilePage.file_id == file_id)
        .order_by(asc(FilePage.page_number))
        .all()
    )
    if not pages:
        return jsonify({"file_id": file_id, "topics": [], "per_page": []})

    per_page = []
    agg = {}
    for pn, topics in pages:
        topics = topics or []
        per_page.append({"page": pn, "topics": topics})
        for t in topics:
            node = agg.setdefault(t, {"topic": t, "count": 0, "pages": []})
            node["count"] += 1
            node["pages"].append(pn)

    topics_sorted = sorted(agg.values(), key=lambda x: (-x["count"], x["topic"]))

    return jsonify({
        "file_id": file_id,
        "topics": topics_sorted,
        "per_page": per_page
    })