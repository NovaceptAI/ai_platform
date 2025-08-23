from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import Progress


tool_progress_bp = Blueprint("tool_progress", __name__, url_prefix="/api/tools")


@tool_progress_bp.get("/overview")
@jwt_required()
def overview():
    """Return latest progress per tool for the current user."""
    uid = get_jwt_identity()

    rows = db.session.execute(
        """
        SELECT DISTINCT ON (tool, user_id)
               id, tool, user_id, percentage, status, created_at, updated_at
        FROM progress
        WHERE user_id = :uid
        ORDER BY tool, user_id, created_at DESC, updated_at DESC
        """,
        {"uid": uid},
    ).mappings().all()

    items = []
    for r in rows:
        updated = r.get("updated_at") or r.get("created_at")
        items.append({
            "tool": r["tool"],
            "percentage": r["percentage"] or 0,
            "status": r["status"],
            "updated_at": updated.isoformat() if updated else None,
        })

    return jsonify({"items": items})