from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import Progress
from app.tasks.ai_summarizer_task import run_ai_summarizer
import uuid
import datetime as dt


ai_summarizer_bp = Blueprint("ai_summarizer", __name__, url_prefix="/api/ai-summarizer")


def _new_progress(user_id, tool_slug, file_id=None):
    p = Progress(
        id=uuid.uuid4(),
        user_id=user_id,
        file_id=file_id,
        tool=tool_slug,
        status="in_progress",
        percentage=0,
        created_at=dt.datetime.utcnow(),
    )
    db.session.add(p)
    db.session.commit()
    return p


@ai_summarizer_bp.post("/start")
@jwt_required()
def start():
    uid = get_jwt_identity()
    data = request.get_json() or {}
    file_id = data.get("file_id")
    p = _new_progress(uid, "ai-summarizer", file_id)
    run_ai_summarizer.apply_async(args=[str(p.id), data], queue="ai_summarizer")
    return jsonify({"progress_id": str(p.id), "status": "queued"}), 202


@ai_summarizer_bp.get("/progress/<progress_id>")
@jwt_required()
def progress(progress_id):
    p = db.session.get(Progress, progress_id)
    if not p:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "id": str(p.id),
        "status": p.status,
        "percentage": p.percentage or 0,
        "result_ready": bool(p.result_json),
    })


@ai_summarizer_bp.get("/results/<progress_id>")
@jwt_required()
def results(progress_id):
    p = db.session.get(Progress, progress_id)
    if not p:
        return jsonify({"error": "not found"}), 404
    if p.status != "completed":
        return jsonify({"error": "not ready", "status": p.status, "percentage": p.percentage or 0}), 409
    return jsonify(p.result_json or {})