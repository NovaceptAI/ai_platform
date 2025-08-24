from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import Progress
from app.tasks.learn_by_drawing_task import run_learn_by_drawing
import uuid
import datetime as dt

learn_by_drawing_bp = Blueprint("learn_by_drawing", __name__, url_prefix="/api/learn-by-drawing")


def _new_progress(user_id, tool_name, file_id=None):
    p = Progress(
        id=uuid.uuid4(),
        user_id=user_id,
        file_id=file_id,
        tool=tool_name,
        status="pending",
        percentage=0,
        created_at=dt.datetime.utcnow(),
    )
    db.session.add(p)
    db.session.commit()
    return p


@learn_by_drawing_bp.post("/start")
@jwt_required()
def start():
    uid = get_jwt_identity()
    data = request.get_json() or {}
    file_id = data.get("file_id")
    p = _new_progress(uid, "Learn by Drawing", file_id)
    run_learn_by_drawing.apply_async(args=[str(p.id), data], queue="learn_by_drawing")
    return jsonify({"progress_id": str(p.id), "status": "queued"}), 202


@learn_by_drawing_bp.get("/progress/<progress_id>")
@jwt_required()
def progress(progress_id):
    p = db.session.get(Progress, progress_id)
    if not p:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "id": str(p.id),
        "status": p.status,
        "percentage": p.percentage or 0,
    })


@learn_by_drawing_bp.get("/results/<progress_id>")
@jwt_required()
def results(progress_id):
    p = db.session.get(Progress, progress_id)
    if not p:
        return jsonify({"error": "not found"}), 404
    if p.status != "done":
        return jsonify({"error": "not ready", "status": p.status, "percentage": p.percentage or 0}), 409
    return jsonify({
        "summary": f"Learn by Drawing placeholder result for progress={progress_id}",
        "chunks": [],
        "meta": {"version": 1},
    })