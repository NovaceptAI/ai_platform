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
# from app.routes.upload import download_blob_to_tmp
from uuid import UUID

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

        files = list(batch.files_json or [])
        if not files:
            # Nothing in the batch; mark complete with 0
            batch.percentage = 100
            batch.status = "completed"
            db.session.commit()
            return jsonify({
                "batch_id": str(batch.id),
                "status": batch.status,
                "percentage": batch.percentage,
                "files": []
            })

        total = len(files)
        sum_pct = 0
        completed = 0
        refreshed = []

        for spec in files:
            pid = spec.get("progress_id")
            # Safely coerce to UUID for querying
            pr = None
            if pid:
                try:
                    pr = db.session.query(Progress).get(UUID(pid))
                except Exception:
                    # fallback: some DBs accept string UUID lookups
                    pr = db.session.query(Progress).get(pid)

            # Copy through & overlay live values
            spec_out = dict(spec)
            if pr:
                spec_out["percentage"] = pr.percentage or 0
                spec_out["status"] = pr.status or "in_progress"
                if pr.status == "completed" or (pr.percentage or 0) >= 100:
                    completed += 1
                sum_pct += (pr.percentage or 0)
            else:
                # If progress not found, keep prior values but don’t skew average
                spec_out.setdefault("percentage", 0)
                spec_out.setdefault("status", "in_progress")
                sum_pct += int(spec_out["percentage"])

            refreshed.append(spec_out)

        overall = int(sum_pct / max(1, total))
        batch.files_json = refreshed
        batch.percentage = overall
        batch.status = "completed" if completed == total else "in_progress"
        db.session.commit()

        return jsonify({
            "batch_id": str(batch.id),
            "status": batch.status,
            "percentage": overall,
            "files": refreshed
        }), 200

    except Exception as e:
        current_app.logger.exception("[BatchSummarizer] progress failed")
        db.session.rollback()
        return jsonify({"error": str(e) or "Failed to fetch batch progress"}), 500