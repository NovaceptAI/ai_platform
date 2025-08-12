from flask import Blueprint, request, jsonify
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.tasks.segmenter_tasks import build_segments_for_file
from app.services.stages.discover.segmenter_service import SegmenterService

segmenter_bp = Blueprint("segmenter", __name__)

def _get_user_id():
    return request.headers.get("X-User-Id") or (request.json or {}).get("user_id")

@segmenter_bp.route("/start", methods=["POST"])
def start_segments():
    """
    Body: { "file_id": "...", "user_id": "...", "force": false }
    Enqueue segmentation task with progress tracking.
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
        tool="segments", status="in_progress", percentage=0
    ))
    db.session.commit()

    build_segments_for_file.apply_async(args=[str(file_id), str(prog_id), force], countdown=0)
    return jsonify({"message":"Processing segments","progress_id":str(prog_id),"file_id":str(file_id)}), 202


@segmenter_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def segments_progress(progress_id):
    p = db.session.query(Progress).get(progress_id)
    if not p: return jsonify({"error":"Not found"}), 404
    return jsonify({
        "progress_id": str(p.id),
        "file_id": str(p.file_id),
        "tool": p.tool,
        "status": p.status,
        "percentage": p.percentage or 0
    })


@segmenter_bp.route("/results", methods=["GET"])
def segments_results():
    """
    Returns per-page segments and a merged outline for the document.
    If FilePage.page_segments exists we use it; else we compute on-the-fly.
    """
    file_id = request.args.get("file_id")
    if not file_id:
        return jsonify({"error":"file_id required"}), 400

    has_col = hasattr(FilePage, "page_segments")
    svc = SegmenterService()

    per_page = []
    if has_col:
        rows = (db.session.query(FilePage.page_number, FilePage.page_segments)
                .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())
        for pn, segs in rows:
            per_page.append({"page": pn, "segments": (segs or [])})
    else:
        rows = (db.session.query(FilePage.page_number, FilePage.page_text)
                .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())
        for pn, txt in rows:
            per_page.append({"page": pn, "segments": svc.segment_page(txt or "")})

    merged = svc.merge_outline([(pp["page"], pp["segments"]) for pp in per_page])
    return jsonify({"file_id": file_id, "per_page": per_page, "outline": merged})