from flask import Blueprint, request, jsonify
from uuid import uuid4
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.tasks.creative_prompts_tasks import build_prompts_for_file
from app.services.stages.create.creative_prompts_service import CreativePromptsService

creative_prompts_bp = Blueprint("creative_prompts", __name__)

def _get_user_id():
    return request.headers.get("X-User-Id") or (request.json or {}).get("user_id")

@creative_prompts_bp.route("/start", methods=["POST"])
def start_creative_prompts():
    """
    Body: { "file_id": "...", "user_id": "...", "force": false }
    Creates Progress(tool='creative_writing_prompts') and enqueues Celery task.
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
        tool="creative_writing_prompts", status="in_progress", percentage=0
    ))
    db.session.commit()

    build_prompts_for_file.apply_async(args=[str(file_id), str(prog_id), force], countdown=0)
    return jsonify({"message": "Processing creative prompts",
                    "progress_id": str(prog_id),
                    "file_id": str(file_id)}), 202


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
    Returns both views:
    - per_page: [{page, prompts:[{prompt, genre, tone, tags:[]}] }]
    - merged:   [{prompt, genre, tone, tags:[], pages:[...]}] (deduped by prompt text)
    Query: ?file_id=...
    """
    file_id = request.args.get("file_id")
    if not file_id:
        return jsonify({"error": "file_id required"}), 400

    rows = (db.session.query(FilePage.page_number, FilePage.page_text)
            .filter_by(file_id=file_id)
            .order_by(asc(FilePage.page_number))
            .all())

    has_col = hasattr(FilePage, "page_prompts")
    if has_col:
        rows2 = (db.session.query(FilePage.page_number, FilePage.page_prompts)
                 .filter_by(file_id=file_id)
                 .order_by(asc(FilePage.page_number))
                 .all())
        per_page = [{"page": pn, "prompts": (pls or [])} for pn, pls in rows2]
    else:
        svc = CreativePromptsService()
        per_page = [{"page": pn, "prompts": svc.generate_prompts_from_text(txt or "")} for pn, txt in rows]

    # merged unique by normalized prompt text
    seen = {}
    for pp in per_page:
        page_no = pp["page"]
        for it in (pp.get("prompts") or []):
            key = (it.get("prompt") or "").strip().lower()
            if not key:
                continue
            node = seen.get(key)
            if not node:
                node = {
                    "prompt": (it.get("prompt") or "").strip(),
                    "genre": (it.get("genre") or None),
                    "tone": (it.get("tone") or None),
                    "tags": (it.get("tags") or [])[:6],
                    "pages": [page_no],
                }
                seen[key] = node
            else:
                if page_no not in node["pages"]:
                    node["pages"].append(page_no)

    merged = list(seen.values())
    merged.sort(key=lambda x: x["prompt"].lower())
    for m in merged:
        m["pages"].sort()

    return jsonify({"file_id": file_id, "per_page": per_page, "merged": merged})