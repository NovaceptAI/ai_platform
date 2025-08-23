from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import Progress
from app.tasks.interactive-quiz-creator_task import run_interactive_quiz_creator
import uuid
import datetime as dt


interactive_quiz_creator_bp = Blueprint("interactive_quiz_creator", __name__, url_prefix="/api/interactive-quiz-creator")


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


@interactive_quiz_creator_bp.post("/start")
@jwt_required()
def start():
    uid = get_jwt_identity()
    data = request.get_json() or {}
    file_id = data.get("file_id")
    p = _new_progress(uid, "interactive-quiz-creator", file_id)
    run_interactive_quiz_creator.apply_async(args=[str(p.id), data], queue="interactive_quiz_creator")
    return jsonify({"progress_id": str(p.id), "status": "queued"}), 202


@interactive_quiz_creator_bp.get("/progress/<progress_id>")
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


@interactive_quiz_creator_bp.get("/results/<progress_id>")
@jwt_required()
def results(progress_id):
    p = db.session.get(Progress, progress_id)
    if not p:
        return jsonify({"error": "not found"}), 404
    if p.status != "completed":
        return jsonify({"error": "not ready", "status": p.status, "percentage": p.percentage or 0}), 409
    return jsonify(p.result_json or {})