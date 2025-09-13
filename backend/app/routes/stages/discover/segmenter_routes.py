from flask import Blueprint, request, jsonify
from uuid import uuid4
from sqlalchemy import asc, func
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import FilePage, Progress
from app.models.analysis_results import SegmentResult  # NEW
from app.tasks.segmenter_tasks import build_segments_for_file
from app.services.stages.discover.segmenter_service import SegmenterService

segmenter_bp = Blueprint("segmenter", __name__)

def _get_user_id():
    return get_jwt_identity()

@segmenter_bp.route("/start", methods=["POST"])
@jwt_required()
def start_segments():
    """
    Body: { "file_id": "...", "force": false }
    If a SegmentResult exists and force=false, return cached.
    Else if per-page segments already exist and force=false, also return cached (we'll merge on /results).
    Otherwise enqueue the task.
    """
    data = request.get_json(force=True)
    file_id = data.get("file_id")
    force = bool(data.get("force", False))
    user_id = _get_user_id()

    if not file_id:
        return jsonify({"error": "file_id required"}), 400

    exists = db.session.query(FilePage.id).filter_by(file_id=file_id).limit(1).first()
    if not exists:
        return jsonify({"error": "No pages for file_id"}), 404

    # 1) Prefer persisted SegmentResult cache
    if not force:
        existing = (
            db.session.query(SegmentResult)
            .filter_by(file_id=file_id, is_active=True)
            .first()
        )
        if existing:
            return jsonify({
                "message": "Segments already available",
                "cached": True,
                "file_id": str(file_id),
                "result_id": str(existing.id),
                "num_segments": existing.num_segments,
                "source": "segments_table"
            }), 200

    # 2) If per-page segments already exist, treat as cached too (we'll merge in /results)
    has_col = hasattr(FilePage, "page_segments")
    if has_col and not force:
        any_segs = (
            db.session.query(func.count(FilePage.id))
            .filter(FilePage.file_id == file_id, FilePage.page_segments.isnot(None))
            .scalar()
        )
        if any_segs and any_segs > 0:
            return jsonify({
                "message": "Per-page segments already available",
                "cached": True,
                "file_id": str(file_id),
                "pages_with_segments": int(any_segs),
                "source": "file_pages"
            }), 200

    # 3) Create progress & enqueue
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
    Returns per-page segments and a merged outline.
    Prefers persisted SegmentResult for the outline; per-page is read from FilePage if present,
    else computed on the fly.
    """
    file_id = request.args.get("file_id")
    if not file_id:
        return jsonify({"error":"file_id required"}), 400

    # 1) Per-page list
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

    # 2) Prefer persisted outline
    existing = (
        db.session.query(SegmentResult)
        .filter_by(file_id=file_id, is_active=True)
        .first()
    )
    if existing and (existing.segments or []) != []:
        outline = existing.segments or []
        return jsonify({
            "file_id": file_id,
            "per_page": per_page,
            "outline": outline,
            "version": existing.version
        })

    # 3) Fallback: compute outline now
    outline = svc.merge_outline([(pp["page"], pp["segments"]) for pp in per_page])
    return jsonify({"file_id": file_id, "per_page": per_page, "outline": outline})