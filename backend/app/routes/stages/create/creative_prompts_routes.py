from flask import Blueprint, request, jsonify
from uuid import uuid4
from sqlalchemy import asc, desc, or_
from app.db import db
from app.models import FilePage, Progress, UploadedFile
from app.tasks.creative_prompts_tasks import build_prompts_for_file
from app.services.stages.create.creative_prompts_service import CreativePromptsService

creative_prompts_bp = Blueprint("creative_prompts", __name__)

import uuid

try:
    from app.models import UploadedFile
except Exception:
    UploadedFile = None

def _get_user_id():
    # default to 'admin' if not provided
    return request.headers.get("X-User-Id") or (request.json or {}).get("user_id") or "admin"

def _is_uuid(val: str) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except Exception:
        return False

def _resolve_file_id_by_filename(filename: str, user_id: str = None) -> str:
    """Map a vault filename (stored name) to its UUID file_id."""
    if not filename:
        return None

    s = db.session

    # Prefer UploadedFile table if available
    if UploadedFile is not None:
        conds = []
        if hasattr(UploadedFile, "stored_file_name"):
            conds.append(UploadedFile.stored_file_name == filename)
        if hasattr(UploadedFile, "stored_name"):
            conds.append(UploadedFile.stored_name == filename)
        if hasattr(UploadedFile, "original_file_name"):
            conds.append(UploadedFile.original_file_name == filename)
        if hasattr(UploadedFile, "filename"):
            conds.append(UploadedFile.filename == filename)

        if conds:
            q = s.query(UploadedFile.id).filter(or_(*conds))
            if user_id and hasattr(UploadedFile, "user_id"):
                q = q.filter(UploadedFile.user_id == user_id)
            if hasattr(UploadedFile, "created_at"):
                q = q.order_by(desc(UploadedFile.created_at))
            row = q.first()
            if row:
                return str(row[0])

    # Fallback (only if you keep filename on pages; otherwise skip)
    try:
        fp_q = s.query(FilePage.file_id)
        if hasattr(FilePage, "stored_file_name"):
            fp_q = fp_q.filter(FilePage.stored_file_name == filename)
        elif hasattr(FilePage, "source_name"):
            fp_q = fp_q.filter(FilePage.source_name == filename)
        elif hasattr(FilePage, "file_name"):
            fp_q = fp_q.filter(FilePage.file_name == filename)
        else:
            return None
        row2 = fp_q.order_by(asc(FilePage.page_number)).first()
        if row2:
            return str(row2[0])
    except Exception:
        pass

    return None

@creative_prompts_bp.route("/start", methods=["POST"])
def start_creative_prompts():
    """
    Body: {
        "file_id": "...",
        "filename": "..." (optional, for vault files),
        "user_id": "...",
        "num_prompts": 10,
        "genre": "mixed" (mixed/fantasy/scifi/mystery/romance/horror),
        "force": false
    }
    Creates Progress(tool='creative_writing_prompts') and enqueues Celery task.
    """
    data = request.get_json(force=True)
    file_id  = data.get("file_id")
    filename = data.get("filename") or data.get("stored_name")
    user_id  = _get_user_id()
    num_prompts = int(data.get("num_prompts") or 10)
    genre = (data.get("genre") or "mixed").lower()
    force      = bool(data.get("force", False))

    # If no UUID, but a filename was provided, resolve it
    if (not file_id or not _is_uuid(file_id)) and filename:
        file_id = _resolve_file_id_by_filename(filename, user_id=user_id)

    # Also handle the case where client mistakenly sent filename in file_id
    if file_id and not _is_uuid(file_id):
        maybe = _resolve_file_id_by_filename(file_id, user_id=user_id)
        file_id = maybe or None

    if not file_id:
        return jsonify({"error": "file_id or filename required"}), 400

    exists = db.session.query(FilePage.id).filter_by(file_id=file_id).limit(1).first()
    if not exists:
        return jsonify({"error": "No pages for file_id"}), 404

    prog_id = uuid4()
    db.session.add(Progress(
        id=prog_id, file_id=file_id, user_id=user_id,
        tool="creative_writing_prompts", status="in_progress", percentage=0
    ))
    db.session.commit()

    build_prompts_for_file.apply_async(
        args=[str(file_id), str(prog_id), int(num_prompts), genre, force],
        countdown=0
    )
    return jsonify({
        "message": "Generating creative writing prompts",
        "progress_id": str(prog_id),
        "file_id": str(file_id)
    }), 202


@creative_prompts_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def creative_prompts_progress(progress_id):
    p = db.session.query(Progress).get(progress_id)
    if not p:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "progress_id": str(p.id),
        "file_id": str(p.file_id),
        "tool": p.tool,
        "status": p.status,
        "percentage": p.percentage or 0
    })


@creative_prompts_bp.route("/results", methods=["GET"])
def creative_prompts_results():
    """
    Returns:
    - prompts_set: {title, genre, prompts:[{prompt, genre, tone, tags:[], description}]}
    Query: ?file_id=...&num_prompts=10&genre=mixed
    """
    file_id   = request.args.get("file_id")
    filename  = request.args.get("filename") or request.args.get("stored_name")
    user_id   = request.headers.get("X-User-Id") or "admin"
    num_prompts = int(request.args.get("num_prompts") or 10)
    genre = (request.args.get("genre") or "mixed").lower()

    # Resolve if needed
    if (not file_id or not _is_uuid(file_id)) and filename:
        file_id = _resolve_file_id_by_filename(filename, user_id=user_id)

    if file_id and not _is_uuid(file_id):
        maybe = _resolve_file_id_by_filename(file_id, user_id=user_id)
        file_id = maybe or None

    if not file_id:
        return jsonify({"error": "file_id or filename required"}), 400

    # Try to get results from Progress table first (stored by the task)
    # Note: We need to filter by checking result_data->>'file_id' matches our file_id
    # For PostgreSQL JSONB queries
    progress_records = (
        db.session.query(Progress)
        .filter(
            Progress.tool == "creative_prompts",
            Progress.status == "completed",
            Progress.result_data.isnot(None)
        )
        .order_by(Progress.completed_at.desc())
        .limit(20)  # Check last 20 completed tasks
        .all()
    )

    # Find the matching progress for this file_id
    matching_progress = None
    # log.info(f"[CreativePrompts] Looking for file_id: {file_id} (type: {type(file_id)})")
    for prog in progress_records:
        if prog.result_data:
            stored_file_id = prog.result_data.get("file_id")
            # log.debug(f"[CreativePrompts] Checking progress {prog.id}: stored_file_id={stored_file_id} (type: {type(stored_file_id)})")
            # Compare as strings to handle UUID vs string comparison
            if str(stored_file_id) == str(file_id):
                matching_progress = prog
                # log.info(f"[CreativePrompts] Found matching progress: {prog.id}")
                break

    # If we have stored results for this file, return them
    if matching_progress and matching_progress.result_data:
        result_data = matching_progress.result_data
        title = f"Creative Writing Prompts from file {str(file_id)[:6]}…"
        return jsonify({
            "file_id": file_id,
            "per_page": result_data.get("per_page", []),
            "prompts_set": {
                "title": title,
                "genre": result_data.get("genre", genre),
                "prompts": result_data.get("prompts", [])
            }
        })

    # Fallback: Try to fetch from FilePage.page_prompts if column exists
    has_col = hasattr(FilePage, "page_prompts")
    if has_col:
        rows2 = (db.session.query(FilePage.page_number, FilePage.page_prompts)
                 .filter_by(file_id=file_id)
                 .order_by(asc(FilePage.page_number))
                 .all())
        per_page = [{"page": pn, "prompts": (pls or [])} for pn, pls in rows2]

        # Flatten and deduplicate
        seen = set()
        flat = []
        for pp in per_page:
            for pr in (pp.get("prompts") or []):
                key = (pr.get("prompt") or "").strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    flat.append(pr)

        prompts = flat[:max(1, num_prompts)]
        title = f"Creative Writing Prompts from file {str(file_id)[:6]}…"

        return jsonify({
            "file_id": file_id,
            "per_page": per_page,
            "prompts_set": {
                "title": title,
                "genre": genre,
                "prompts": prompts
            }
        })

    # No results found
    return jsonify({
        "error": "No results found. Please generate prompts first using the /start endpoint.",
        "file_id": file_id
    }), 404
