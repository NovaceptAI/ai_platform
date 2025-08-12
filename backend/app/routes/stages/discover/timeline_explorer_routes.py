from flask import Blueprint, request, jsonify, current_app
import os, tempfile, uuid, json
from app.db import db
from uuid import uuid4
from app.models import Progress, UploadedFile
from app.tasks.timeline_explorer_tasks import build_timeline
from app.services.stages.discover.timeline_explorer_service import TimelineExplorerService

# vault downloader (optional)
try:
    from app.routes.upload import download_blob_to_tmp
except Exception:
    download_blob_to_tmp = None

timeline_explorer_bp = Blueprint("timeline_explorer", __name__)

@timeline_explorer_bp.route("/start", methods=["POST"])
def timeline_start():
    tmp_path = None
    try:
        method = "category"
        payload = {}
        file_id_for_progress = None
        user_id_for_progress = "system"

        # ---- JSON path ----
        if request.is_json or (request.content_type or "").startswith("application/json"):
            data = request.get_json(force=True, silent=True) or {}
            method = (data.get("method") or "category").lower()

            if method == "category":
                cat = (data.get("category") or "").strip()
                if not cat:
                    return jsonify({"error": "Missing category"}), 400
                payload = {"category": cat}

            elif method == "text":
                txt = (data.get("text") or "").strip()
                if not txt:
                    return jsonify({"error": "Missing text"}), 400
                payload = {"text": txt}

            elif method == "document":
                if not data.get("fromVault"):
                    return jsonify({"error": "Document method requires fromVault+filename"}), 400

                filename = (data.get("filename") or "").strip()
                if not filename:
                    return jsonify({"error": "Missing filename for fromVault"}), 400

                # --- DB lookup: tie progress to the backing UploadedFile ---
                uploaded_file = (
                    db.session.query(UploadedFile)
                    .filter_by(stored_file_name=filename)  # or stored_file_name if that's your column
                    .first()
                )
                if not uploaded_file:
                    return jsonify({"error": "Uploaded file not found in DB"}), 404

                file_id_for_progress = uploaded_file.id
                user_id_for_progress = uploaded_file.user_id
                payload = {"fromVault": True, "filename": filename}
            else:
                return jsonify({"error": "Invalid method"}), 400

        else:
            return jsonify({"error": "No valid payload provided"}), 400

        # --- Create Progress row ---
        # If your progress.file_id is NOT NULL, ensure file_id_for_progress is set (i.e., only document runs).
        # If you plan to support category/text without a file, allow NULLs in schema:
        # ALTER TABLE progress ALTER COLUMN file_id DROP NOT NULL;
        progress = Progress(
            id=uuid4(),
            user_id=user_id_for_progress,
            file_id=file_id_for_progress,       # None for category/text; actual UUID for document
            status="in_progress",
            tool="timeline",
            percentage=0,
        )
        db.session.add(progress)
        db.session.commit()

        # Kick off Celery
        build_timeline.apply_async(
            args=[str(progress.id), method, payload],
            countdown=0
        )

        return jsonify({"progress_id": str(progress.id)}), 200

    except Exception as e:
        current_app.logger.exception("[Timeline] start failed")
        return jsonify({"error": str(e) or "Failed to start timeline build."}), 500

@timeline_explorer_bp.route("/progress/<progress_id>", methods=["GET"])
def timeline_progress(progress_id):
    prog = db.session.query(Progress).get(progress_id)
    if not prog:
        return jsonify({"error":"not_found"}), 404
    # When using status to store result JSON, keep presenting a simple status surface
    status = "completed" if (prog.percentage or 0) >= 100 and prog.status not in ("failed","in_progress") else (prog.status or "in_progress")
    # If the task stored JSON in status, present "completed" to front-end and let it call /result to fetch
    if isinstance(status, str) and status.startswith("{"):
        status = "completed"
    return jsonify({"percentage": prog.percentage or 0, "status": status}), 200

@timeline_explorer_bp.route("/result/<progress_id>", methods=["GET"])
def timeline_result(progress_id):
    prog = db.session.query(Progress).get(progress_id)
    if not prog:
        return jsonify({"error":"not_found"}), 404
    try:
        # We stashed JSON in status as {"result": {...}}
        data = json.loads(prog.status) if prog.status and prog.status.startswith("{") else {}
        return jsonify(data.get("result") or {"timeline": []}), 200
    except Exception:
        return jsonify({"timeline": []}), 200
