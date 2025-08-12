from flask import Blueprint, request, jsonify
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.tasks.doc_analysis_tasks import build_doc_analysis_for_file
from app.services.stages.doc_analysis_service import DocAnalysisService

doc_bp = Blueprint("doc_analysis", __name__)

def _get_user_id():
    return request.headers.get("X-User-Id") or (request.json or {}).get("user_id")

@doc_bp.route("/start", methods=["POST"])
def start_doc_analysis():
    data = request.get_json(force=True)
    file_id = data.get("file_id")
    force = bool(data.get("force", False))
    user_id = _get_user_id()
    if not file_id or not user_id:
        return jsonify({"error":"file_id and user_id required"}), 400

    exists = db.session.query(FilePage.id).filter_by(file_id=file_id).limit(1).first()
    if not exists:
        return jsonify({"error":"No pages for file_id"}), 404

    prog_id = uuid4()
    db.session.add(Progress(
        id=prog_id, file_id=file_id, user_id=user_id,
        tool="doc_analysis", status="in_progress", percentage=0
    ))
    db.session.commit()

    build_doc_analysis_for_file.apply_async(args=[str(file_id), str(prog_id), force], countdown=0)
    return jsonify({"message":"Processing document analysis","progress_id":str(prog_id),"file_id":str(file_id)}), 202


@doc_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def doc_analysis_progress(progress_id):
    p = db.session.query(Progress).get(progress_id)
    if not p: return jsonify({"error":"Not found"}), 404
    return jsonify({
        "progress_id": str(p.id),
        "file_id": str(p.file_id),
        "tool": p.tool,
        "status": p.status,
        "percentage": p.percentage or 0
    })


@doc_bp.route("/results", methods=["GET"])
def doc_analysis_results():
    """
    Recompute per-page (as requested) and aggregate. Also supports on-demand mind map:
    - Query: ?file_id=...&mind_map=true
    """
    file_id = request.args.get("file_id")
    want_map = (request.args.get("mind_map","false").lower() == "true")
    if not file_id:
        return jsonify({"error":"file_id required"}), 400

    svc = DocAnalysisService()

    # per-page compute
    rows = (db.session.query(FilePage.page_number, FilePage.page_text)
            .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())
    per_page = []
    for pn, txt in rows:
        per_page.append({"page": pn, "analysis": svc.analyze_page(txt or "")})

    doc_summary = svc.aggregate([(pp["page"], pp["analysis"]) for pp in per_page])

    data = {"file_id": file_id, "per_page": per_page, "doc": doc_summary}

    if want_map:
        full_text = " ".join((txt or "") for _, txt in rows)
        data["mind_map"] = svc.build_mind_map(full_text)

    return jsonify(data)


@doc_bp.route("/mind_map", methods=["POST"])
def doc_analysis_mind_map():
    """
    On-demand mind map for an existing file (uses all page_text).
    Body: { "file_id": "..." }
    """
    data = request.get_json(force=True)
    file_id = data.get("file_id")
    if not file_id:
        return jsonify({"error":"file_id required"}), 400

    rows = (db.session.query(FilePage.page_text)
            .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())
    full_text = " ".join((r[0] or "") for r in rows)
    svc = DocAnalysisService()
    return jsonify(svc.build_mind_map(full_text))