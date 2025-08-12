from flask import Blueprint, request, jsonify
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.tasks.sentiment_tasks import build_sentiment_for_file
from app.services.stages.discover.sentiment_service import SentimentService

sentiment_bp = Blueprint("sentiment", __name__)

def _get_user_id():
    return request.headers.get("X-User-Id") or (request.json or {}).get("user_id")

@sentiment_bp.route("/start", methods=["POST"])
def start_sentiment():
    """
    Body: { "file_id": "...", "user_id": "...", "force": false }
    Starts page-by-page sentiment task with progress.
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
        tool="sentiment", status="in_progress", percentage=0
    ))
    db.session.commit()

    build_sentiment_for_file.apply_async(args=[str(file_id), str(prog_id), force], countdown=0)
    return jsonify({"message":"Processing sentiment","progress_id":str(prog_id),"file_id":str(file_id)}), 202


@sentiment_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def sentiment_progress(progress_id):
    p = db.session.query(Progress).get(progress_id)
    if not p: return jsonify({"error":"Not found"}), 404
    return jsonify({
        "progress_id": str(p.id),
        "file_id": str(p.file_id),
        "tool": p.tool,
        "status": p.status,
        "percentage": p.percentage or 0
    })


@sentiment_bp.route("/results", methods=["GET"])
def sentiment_results():
    """
    Returns both per-page and doc-wise sentiment.
    For now, this recomputes on demand (as requested). If you add FilePage.page_sentiment JSON,
    we’ll prefer the stored values.
    """
    file_id = request.args.get("file_id")
    if not file_id:
        return jsonify({"error":"file_id required"}), 400

    has_col = hasattr(FilePage, "page_sentiment")
    svc = SentimentService()

    per_page = []
    if has_col:
        rows = (db.session.query(FilePage.page_number, FilePage.page_sentiment)
                .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())
        for pn, sdict in rows:
            per_page.append({"page": pn, "sentiment": sdict or {"label":"neutral","score":0.0,"rationale":""}})
    else:
        rows = (db.session.query(FilePage.page_number, FilePage.page_text)
                .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())
        for pn, txt in rows:
            per_page.append({"page": pn, "sentiment": svc.analyze_page(txt or "")})

    # Aggregate doc-wise
    doc_summary = svc.aggregate_document([(pp["page"], pp["sentiment"]) for pp in per_page])

    return jsonify({"file_id": file_id, "per_page": per_page, "doc": doc_summary})