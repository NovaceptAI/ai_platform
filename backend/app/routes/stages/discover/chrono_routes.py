from flask import Blueprint, request, jsonify
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.tasks.chrono_tasks import build_chronology_for_file
from app.services.stages.discover.chrono_service import ChronologyService

chrono_bp = Blueprint("chronology", __name__)

def _get_user_id():
    return request.headers.get("X-User-Id") or (request.json or {}).get("user_id")

@chrono_bp.route("/start", methods=["POST"])
def start_chronology():
    """
    Body: { "file_id": "...", "user_id": "...", "force": false }
    Creates Progress(tool='chronology') and enqueues Celery task.
    """
    data = request.get_json(force=True)
    file_id = data.get("file_id")
    force = bool(data.get("force", False))
    user_id = _get_user_id()
    if not file_id or not user_id:
        return jsonify({"error": "file_id and user_id required"}), 400

    exists = db.session.query(FilePage.id).filter_by(file_id=file_id).limit(1).first()
    if not exists:
        return jsonify({"error": "No pages for file_id"}), 404

    prog_id = uuid4()
    db.session.add(Progress(
        id=prog_id, file_id=file_id, user_id=user_id,
        tool="chronology", status="in_progress", percentage=0
    ))
    db.session.commit()

    build_chronology_for_file.apply_async(args=[str(file_id), str(prog_id), force], countdown=0)
    return jsonify({"message":"Processing chronology","progress_id":str(prog_id),"file_id":str(file_id)}), 202


@chrono_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def chronology_progress(progress_id):
    p = db.session.query(Progress).get(progress_id)
    if not p: return jsonify({"error":"Not found"}), 404
    return jsonify({
        "progress_id": str(p.id),
        "file_id": str(p.file_id),
        "tool": p.tool,
        "status": p.status,
        "percentage": p.percentage or 0
    })


@chrono_bp.route("/results", methods=["GET"])
def chronology_results():
    """
    Returns both views:
    - per_page: [{page, events:[{date,title,desc}]}]
    - merged:   [{date,title,desc,pages:[...]}] sorted by date/title
    Query: ?file_id=...
    """
    file_id = request.args.get("file_id")
    if not file_id:
        return jsonify({"error":"file_id required"}), 400

    rows = (db.session.query(FilePage.page_number, FilePage.page_text)
            .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())

    # If you added a page_chronology column, prefer it; else compute quickly via service
    has_col = hasattr(FilePage, "page_chronology")
    if has_col:
        rows2 = (db.session.query(FilePage.page_number, FilePage.page_chronology)
                 .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())
        per_page = [{"page": pn, "events": (evs or [])} for pn, evs in rows2]
    else:
        svc = ChronologyService()
        per_page = [{"page": pn, "events": svc.extract_events_from_text(txt or "")} for pn, txt in rows]

    svc2 = ChronologyService()  # rotate independently if needed
    merged = svc2.merge_events([(pp["page"], pp["events"]) for pp in per_page])

    return jsonify({"file_id": file_id, "per_page": per_page, "merged": merged})