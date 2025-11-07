from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import Progress
from app.tasks.ai_presentation_builder_task import run_ai_presentation_builder
import uuid, datetime as dt

ai_presentation_builder_bp = Blueprint("ai_presentation_builder", __name__, url_prefix="/api/ai-presentation-builder")

def _new_progress(uid, tool_name, file_id=None):
    p = Progress(
        id=uuid.uuid4(),
        user_id=uid,
        file_id=file_id,
        tool_name=tool_name,
        status="pending",
        percentage=0,
        created_at=dt.datetime.utcnow(),
    )
    db.session.add(p); db.session.commit()
    return p

@ai_presentation_builder_bp.post("/start")
@jwt_required()
def start():
    uid = get_jwt_identity()
    data = request.get_json() or {}
    p = _new_progress(uid, "AI Presentation Builder", data.get("file_id"))
    run_ai_presentation_builder.apply_async(args=[str(p.id), data])  # default queue OK
    return jsonify({"progress_id": str(p.id), "status": "queued"}), 202

@ai_presentation_builder_bp.get("/progress/<progress_id>")
@jwt_required()
def progress(progress_id):
    p = db.session.get(Progress, progress_id)
    if not p: return jsonify({"error": "not found"}), 404
    return jsonify({"id": str(p.id), "status": p.status, "percentage": p.percentage or 0,
                    "has_result": bool((p.extra or {}).get("result")) if hasattr(p, "extra") else False})

@ai_presentation_builder_bp.get("/results/<progress_id>")
@jwt_required()
def results(progress_id):
    p = db.session.get(Progress, progress_id)
    if not p: return jsonify({"error": "not found"}), 404
    if p.status != "done":
        return jsonify({"error": "not ready", "status": p.status, "percentage": p.percentage or 0}), 409
    if p.extra and isinstance(p.extra, dict) and "result" in p.extra:
        return jsonify(p.extra["result"])
    return jsonify({"title":"AI Presentation Builder","note":"No result saved"}), 200