from flask import Blueprint, request, jsonify
from uuid import uuid4
from sqlalchemy import asc
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import FilePage, Progress
from app.models.analysis_results import ChronologyResult
from app.tasks.chrono_tasks import build_chronology_for_file
from app.services.stages.discover.chrono_service import ChronologyService

chrono_bp = Blueprint("chronology", __name__)

def _get_user_id():
    return get_jwt_identity()

def _dated_only(items):
    """Keep only events that have a non-empty 'date' string."""
    out = []
    for e in (items or []):
        if isinstance(e, dict):
            d = e.get("date")
            if isinstance(d, str) and d.strip():
                out.append(e)
    return out

@chrono_bp.route("/start", methods=["POST"])
@jwt_required()
def start_chronology():
    """
    Body: { "file_id": "...", "force": false }
    Creates Progress(tool='chronology') and enqueues Celery task.
    If a persisted ChronologyResult exists and force=false, returns cached result.
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

    # CACHE CHECK (return persisted result if available and not forced)
    if not force:
        existing = (
            db.session.query(ChronologyResult)
            .filter_by(file_id=file_id, is_active=True)
            .first()
        )
        if existing:
            return jsonify({
                "message": "Chronology already available",
                "cached": True,
                "file_id": str(file_id),
                "result_id": str(existing.id),
                "bounds": {
                    "start_date": existing.start_date.isoformat() if existing.start_date else None,
                    "end_date": existing.end_date.isoformat() if existing.end_date else None,
                }
            }), 200

    prog_id = uuid4()
    db.session.add(Progress(
        id=prog_id, file_id=file_id, user_id=user_id,
        tool="chronology", status="in_progress", percentage=0
    ))
    db.session.commit()

    build_chronology_for_file.apply_async(args=[str(file_id), str(prog_id), force], countdown=0)
    return jsonify({"message": "Processing chronology", "progress_id": str(prog_id), "file_id": str(file_id)}), 202


@chrono_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def chronology_progress(progress_id):
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


@chrono_bp.route("/results", methods=["GET"])
def chronology_results():
    """
    Returns both views:
    - per_page: [{page, events:[{date,title,desc}]}]  (dated-only)
    - merged:   [{date,title,desc,pages:[...]}]       (dated-only)
    Prefers persisted ChronologyResult; if no dated events exist, returns a clear status.
    Query: ?file_id=...
    """
    file_id = request.args.get("file_id")
    if not file_id:
        return jsonify({"error": "file_id required"}), 400

    # Build per-page view (prefer stored page_chronology if present), FILTER to dated-only
    rows = (db.session.query(FilePage.page_number, FilePage.page_text)
            .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())

    has_col = hasattr(FilePage, "page_chronology")
    if has_col:
        rows2 = (db.session.query(FilePage.page_number, FilePage.page_chronology)
                 .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())
        per_page = [{"page": pn, "events": _dated_only(evs)} for pn, evs in rows2]
    else:
        svc = ChronologyService()
        per_page = [{"page": pn, "events": svc.extract_events_from_text(txt or "")} for pn, txt in rows]

    # Prefer persisted merged chronology if available (still enforce dated-only)
    existing = (
        db.session.query(ChronologyResult)
        .filter_by(file_id=file_id, is_active=True)
        .first()
    )
    if existing:
        merged = _dated_only(existing.events or [])
        no_dates = bool((existing.meta or {}).get("no_dates_found")) or (len(merged) == 0)
        if no_dates:
            return jsonify({
                "file_id": file_id,
                "status": "no_dates_found",
                "message": "No dated events found in this document.",
                "per_page": per_page,
                "merged": []
            })
        bounds = {
            "start_date": existing.start_date.isoformat() if existing.start_date else None,
            "end_date": existing.end_date.isoformat() if existing.end_date else None,
            "granularity": existing.granularity,
            "coverage_ratio": existing.coverage_ratio,
            "version": existing.version,
        }
        return jsonify({"file_id": file_id, "per_page": per_page, "merged": merged, "bounds": bounds})

    # Fallback: compute merged now (ChronologyService already returns dated-only)
    svc2 = ChronologyService()
    merged = svc2.merge_events([(pp["page"], pp["events"]) for pp in per_page])

    if not merged:
        return jsonify({
            "file_id": file_id,
            "status": "no_dates_found",
            "message": "No dated events found in this document.",
            "per_page": per_page,
            "merged": []
        })

    return jsonify({"file_id": file_id, "per_page": per_page, "merged": merged})
