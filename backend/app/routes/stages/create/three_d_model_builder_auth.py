from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import Progress
from app.tasks.three_d_model_builder_task import run_three_d_model_builder
import uuid
import datetime as dt

three_d_model_builder_bp = Blueprint("three_d_model_builder", __name__, url_prefix="/api/3d-model-builder")


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


@three_d_model_builder_bp.post("/start")
@jwt_required()
def start():
    """
    Body: { file_id?: uuid, params?: {...} }
    Creates a Progress row and enqueues Celery job.
    """
    uid = get_jwt_identity()
    data = request.get_json() or {}
    file_id = data.get("file_id")
    p = _new_progress(uid, "3D Model Builder", file_id)

    # Enqueue task
    run_three_d_model_builder.apply_async(args=[str(p.id), data], queue="three_d_model_builder")

    return jsonify({"progress_id": str(p.id), "status": "queued"}), 202


@three_d_model_builder_bp.get("/progress/<progress_id>")
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


@three_d_model_builder_bp.get("/results/<progress_id>")
@jwt_required()
def results(progress_id):
    p = db.session.get(Progress, progress_id)
    if not p:
        return jsonify({"error": "not found"}), 404
    if p.status != "done":
        return jsonify({"error": "not ready", "status": p.status, "percentage": p.percentage or 0}), 409
    # Placeholder result; store to DB if needed in the future
    return jsonify({
        "summary": f"3D Model Builder placeholder result for progress={progress_id}",
        "chunks": [],
        "meta": {"version": 1},
    })