from flask import Blueprint, request, jsonify
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.models.analysis_results import DocumentAnalysisResult
from app.tasks.doc_analysis_tasks import build_doc_analysis_for_file  # UPDATED import
from app.services.stages.doc_analysis_service import DocAnalysisService
from flask_jwt_extended import jwt_required, get_jwt_identity

doc_bp = Blueprint("doc_analysis", __name__)

def _get_user_id():
    return get_jwt_identity()

@doc_bp.route("/start", methods=["POST"])
@jwt_required()
def start_doc_analysis():
    data = request.get_json(force=True)
    file_id = data.get("file_id")
    force = bool(data.get("force", False))
    user_id = _get_user_id()
    if not file_id or not user_id:
        return jsonify({"error": "file_id and user_id required"}), 400

    # Ensure pages exist
    exists = db.session.query(FilePage.id).filter_by(file_id=file_id).limit(1).first()
    if not exists:
        return jsonify({"error": "No pages for file_id"}), 404

    # CACHE CHECK -> return persisted result if present and not forced
    if not force:
        existing = (
            db.session.query(DocumentAnalysisResult)
            .filter_by(file_id=file_id, is_active=True)
            .first()
        )
        if existing:
            return jsonify({
                "message": "Document analysis already available",
                "cached": True,
                "file_id": str(file_id),
                "result_id": str(existing.id),
                "version": existing.version
            }), 200

    # Create progress & dispatch
    prog_id = uuid4()
    db.session.add(Progress(
        id=prog_id, file_id=file_id, user_id=user_id,
        tool="doc_analysis", status="in_progress", percentage=0
    ))
    db.session.commit()

    build_doc_analysis_for_file.apply_async(args=[str(file_id), str(prog_id), force], countdown=0)
    return jsonify({
        "message": "Processing document analysis",
        "progress_id": str(prog_id),
        "file_id": str(file_id)
    }), 202


@doc_bp.route("/progress/<uuid:progress_id>", methods=["GET"])
def doc_analysis_progress(progress_id):
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


@doc_bp.route("/results", methods=["GET"])
def doc_analysis_results():
    """
    Preferred: return persisted DocumentAnalysisResult if available.
    Query: ?file_id=...&mind_map=true
    """
    file_id = request.args.get("file_id")
    want_map = (request.args.get("mind_map", "false").lower() == "true")
    if not file_id:
        return jsonify({"error": "file_id required"}), 400

    # 1) Prefer persisted doc-level result
    rec = (
        db.session.query(DocumentAnalysisResult)
        .filter_by(file_id=file_id, is_active=True)
        .first()
    )
    if rec:
        data = {
            "file_id": str(file_id),
            "doc": {
                "stats": rec.stats,
                "readability": rec.readability,
                "quality_scores": rec.quality_scores,
                "outline": rec.outline,
                "key_points": rec.key_points,
                "risks": rec.risks,
                "recommendations": rec.recommendations,
                "meta": rec.meta,  # includes entities_by_type if task saved it there
            },
            "per_page": []  # not persisted (kept light)
        }

        entities_by_type = (rec.meta or {}).get("entities_by_type") if rec.meta else {}
        kp = rec.key_points or []
        top_tags = [{"tag": (x.get("text") or ""), "count": x.get("count"), "pages": x.get("pages") or []} for x in kp]
        data = {
            "file_id": str(file_id),
            "doc": {
                "totals": rec.stats or {},                  # legacy key
                "entities_by_type": entities_by_type,       # legacy key
                "top_tags": top_tags,                       # legacy key
                # extras (safe to expose)
                "readability": rec.readability,
                "quality_scores": rec.quality_scores,
                "outline": rec.outline,
                "risks": rec.risks,
                "recommendations": rec.recommendations,
            },
            "per_page": []
        }
        if want_map:
            rows = (db.session.query(FilePage.page_text)
                    .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())
            full_text = " ".join((r[0] or "") for r in rows)
            svc = DocAnalysisService()
            data["mind_map"] = svc.build_mind_map(full_text)
        return jsonify(data)

    # 2) Fallback: compute on the fly (old behavior)
    svc = DocAnalysisService()
    rows = (db.session.query(FilePage.page_number, FilePage.page_text)
            .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())
    per_page = [{"page": pn, "analysis": svc.analyze_page(txt or "")} for pn, txt in rows]
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
        return jsonify({"error": "file_id required"}), 400

    rows = (db.session.query(FilePage.page_text)
            .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())
    full_text = " ".join((r[0] or "") for r in rows)
    svc = DocAnalysisService()
    return jsonify(svc.build_mind_map(full_text))