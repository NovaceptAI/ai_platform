# app/routes/stages/discover/summarizer_batch_routes.py
from flask import Blueprint, request, jsonify, current_app, has_request_context
from flask_jwt_extended import jwt_required, get_jwt_identity
import os, tempfile, uuid, json 
from app.db import db
from app.models import UploadedFile, Progress
from app.tasks.summarizer_tasks import summarize_page_batch, summarize_file_kickoff  # your existing task(s)
from app.models import BatchJob  # SQLAlchemy model mapped to batch_jobs
from datetime import datetime
from app.routes.upload import upload_file

try:
    from app.routes.upload import download_blob_to_tmp
except Exception:
    download_blob_to_tmp = None

summ_batch_bp = Blueprint("batch_summarizer", __name__)

def _current_user_id_fallback():
    # Use JWT if available; otherwise fallback (e.g., for local testing)
    if has_request_context():
        try:
            return get_jwt_identity() or "admin"
        except Exception:
            pass
    return "admin"

@summ_batch_bp.route("/start_batch", methods=["POST"])
@jwt_required(optional=True)  # allow both JWT and local dev
def start_batch():
    """
    Body (JSON only):
      { "vault": ["stored_name1", "stored_name2", ...] }  # up to 5

    Returns:
      {
        "batch_id": "...",
        "files": [
          { "file_id", "original_name", "source":"vault", "progress_id", "status", "percentage" }, ...
        ]
      }
    """
    user_id = _current_user_id_fallback()

    try:
        data = request.get_json(force=True, silent=True) or {}
        vault_files = data.get("vault") or []
        if not isinstance(vault_files, list):
            return jsonify({"error": "vault must be an array of stored_names"}), 400

        total = len(vault_files)
        if total == 0:
            return jsonify({"error": "No files provided"}), 400
        if total > 5:
            return jsonify({"error": "You can process up to 5 files at once"}), 400

        # Resolve each stored_name to an UploadedFile row
        file_specs = []
        for stored in vault_files:
            uf = (
                db.session.query(UploadedFile)
                .filter(UploadedFile.stored_file_name == stored)
                .first()
            )
            if not uf:
                return jsonify({"error": f"Vault file not found: {stored}"}), 404

            file_specs.append({
                "file_id": str(uf.id),
                "original_name": uf.original_file_name,
                "source": "vault"
            })

        # Create per-file progress rows
        for spec in file_specs:
            prog = Progress(
                id=uuid.uuid4(),
                user_id=user_id,
                file_id=spec["file_id"],
                tool="summarizer",
                status="in_progress",
                percentage=0,
            )
            db.session.add(prog)
            spec["progress_id"] = str(prog.id)
            spec["status"] = "in_progress"
            spec["percentage"] = 0

        # Create batch job record
        batch = BatchJob(
            id=uuid.uuid4(),
            user_id=user_id,
            tool="summarizer",
            status="in_progress",
            percentage=0,
            files_json=file_specs
        )
        db.session.add(batch)
        db.session.commit()

        # Fan-out per-file kickoff tasks (small stagger optional)
        STAGGER = 3  # seconds
        for idx, spec in enumerate(file_specs):
            summarize_file_kickoff.apply_async(
                args=[spec["file_id"], spec["progress_id"]],
                countdown=idx * STAGGER
            )

        return jsonify({"batch_id": str(batch.id), "files": file_specs}), 200

    except Exception as e:
        current_app.logger.exception("[SummBatch] start failed")
        return jsonify({"error": str(e) or "Failed to start batch"}), 500


@summ_batch_bp.route("/batch_progress/<uuid:batch_id>", methods=["GET"])
@jwt_required(optional=True)  # allow both JWT and local dev
def batch_progress(batch_id):
    try:
        batch = db.session.query(BatchJob).get(batch_id)
        if not batch:
            return jsonify({"error": "Batch not found"}), 404

        # Optionally recompute overall percentage from per-file Progress
        files = batch.files_json or []
        # refresh each file’s percentage/status from Progress table
        refreshed = []
        completed = 0
        for spec in files:
          pr = db.session.query(Progress).filter_by(id=spec.get("progress_id")).first()
          if pr:
              spec["percentage"] = pr.percentage
              spec["status"] = pr.status
          refreshed.append(spec)
          if spec.get("status") == "completed" or (spec.get("percentage") or 0) >= 100:
              completed += 1

        # overall percentage: avg of file percentages (or any rule you prefer)
        overall = int(sum((f.get("percentage") or 0) for f in refreshed) / max(1, len(refreshed)))
        # update batch cached fields
        batch.percentage = overall
        batch.status = "completed" if completed == len(refreshed) else "in_progress"
        batch.files_json = refreshed
        db.session.commit()

        return jsonify({
            "batch_id": str(batch.id),
            "status": batch.status,
            "percentage": overall,
            "files": refreshed
        }), 200
    except Exception as e:
        current_app.logger.exception("[SummBatch] progress failed")
        return jsonify({"error": str(e) or "Failed to read batch progress"}), 500