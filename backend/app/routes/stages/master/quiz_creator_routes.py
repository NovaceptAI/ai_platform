from flask import Blueprint, request, jsonify
from uuid import uuid4
from sqlalchemy import asc, desc, or_
from app.db import db
from app.models import FilePage, Progress, UploadedFile
from app.tasks.quiz_creator_tasks import build_quiz_for_file
from app.services.stages.master.quiz_creator_service import QuizCreatorService

quiz_creator_bp = Blueprint("quiz_creator", __name__)

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

def _get_user_id():
    return request.headers.get("X-User-Id") or (request.json or {}).get("user_id")

@quiz_creator_bp.route("/start", methods=["POST"])
def start_quiz_creator():
    data = request.get_json(force=True)
    file_id  = data.get("file_id")
    filename = data.get("filename") or data.get("stored_name")
    user_id  = _get_user_id()
    n          = int(data.get("n") or 10)
    difficulty = (data.get("difficulty") or "medium").lower()
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
        tool="quiz_creator", status="in_progress", percentage=0
    ))
    db.session.commit()

    build_quiz_for_file.apply_async(args=[str(file_id), str(prog_id), int(n), difficulty, force], countdown=0)
    return jsonify({"message": "Generating quiz",
                    "progress_id": str(prog_id),
                    "file_id": str(file_id)}), 202


@quiz_creator_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def quiz_creator_progress(progress_id):
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


@quiz_creator_bp.route("/results", methods=["GET"])
def quiz_creator_results():
    file_id   = request.args.get("file_id")
    filename  = request.args.get("filename") or request.args.get("stored_name")
    user_id   = request.headers.get("X-User-Id") or "admin"
    n          = int(request.args.get("n") or 10)
    difficulty = (request.args.get("difficulty") or "medium").lower()

    # Resolve if needed
    if (not file_id or not _is_uuid(file_id)) and filename:
        file_id = _resolve_file_id_by_filename(filename, user_id=user_id)

    if file_id and not _is_uuid(file_id):
        maybe = _resolve_file_id_by_filename(file_id, user_id=user_id)
        file_id = maybe or None

    if not file_id:
        return jsonify({"error": "file_id or filename required"}), 400

    # ---- existing logic below (unchanged) ----
    rows = (db.session.query(FilePage.page_number, FilePage.page_text)
            .filter_by(file_id=file_id)
            .order_by(asc(FilePage.page_number))
            .all())

    has_col = hasattr(FilePage, "page_quiz")
    if has_col:
        rows2 = (db.session.query(FilePage.page_number, FilePage.page_quiz)
                 .filter_by(file_id=file_id)
                 .order_by(asc(FilePage.page_number))
                 .all())
        per_page = [{"page": pn, "questions": (qs or [])} for pn, qs in rows2]
    else:
        svc = QuizCreatorService()
        pages_count = max(1, len(rows))
        base_k = max(1, min(6, (n + pages_count - 1) // pages_count))
        per_page = [{"page": pn, "questions": svc.generate_questions_from_text(txt or "", k=base_k, difficulty=difficulty)}
                    for pn, txt in rows]

    seen = set()
    flat = []
    for pp in per_page:
        for q in (pp.get("questions") or []):
            key = (q.get("question") or "").strip().lower()
            if key and key not in seen:
                seen.add(key)
                flat.append(q)

    questions = flat[:max(1, n)]
    title = f"Quiz from file {str(file_id)[:6]}…"

    return jsonify({
        "file_id": file_id,
        "per_page": per_page,
        "quiz": {
            "title": title,
            "difficulty": difficulty,
            "questions": questions
        }
    })