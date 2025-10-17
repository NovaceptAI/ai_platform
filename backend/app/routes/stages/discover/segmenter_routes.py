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
    Gets data from SegmentResult table where segments are stored.
    """
    try:
        file_id = request.args.get("file_id")
        if not file_id:
            return jsonify({"error":"file_id required"}), 400

        # Get existing SegmentResult
        existing = (
            db.session.query(SegmentResult)
            .filter_by(file_id=file_id, is_active=True)
            .first()
        )

        per_page = []
        if existing and existing.segments and isinstance(existing.segments, list):
            # Extract per-page segments from the SegmentResult data
            page_segments_map = {}
            
            for segment in existing.segments:
                if isinstance(segment, dict):
                    # Try different field names for page information
                    page_start = segment.get('page_start') or segment.get('page') or segment.get('start_page') or 1
                    page_end = segment.get('page_end') or segment.get('end_page') or page_start
                    
                    # Ensure page numbers are integers
                    try:
                        page_start = int(page_start)
                        page_end = int(page_end)
                    except (ValueError, TypeError):
                        page_start = page_end = 1
                    
                    # Add this segment to all pages it spans
                    for page_num in range(page_start, page_end + 1):
                        if page_num not in page_segments_map:
                            page_segments_map[page_num] = []
                        page_segments_map[page_num].append(segment)
            
            # Convert to per_page list format
            for page_num in sorted(page_segments_map.keys()):
                per_page.append({
                    "page": page_num, 
                    "segments": page_segments_map[page_num]
                })
        
        # If no per-page data was extracted, get page numbers from FilePage
        if not per_page:
            rows = (db.session.query(FilePage.page_number)
                    .filter_by(file_id=file_id).order_by(asc(FilePage.page_number)).all())
            for (pn,) in rows:
                per_page.append({"page": pn, "segments": []})

        # Return results
        if existing and existing.segments:
            outline = existing.segments or []
            return jsonify({
                "file_id": file_id,
                "per_page": per_page,
                "outline": outline,
                "version": getattr(existing, 'version', 1)
            })
        else:
            return jsonify({
                "file_id": file_id, 
                "per_page": per_page, 
                "outline": [],
                "message": "No segments found. Try running the segmenter first."
            })
    
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500