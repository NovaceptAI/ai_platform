from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db

# This blueprint provides latest progress per tool for the current user
# Uses raw SQL for DISTINCT ON by (tool, user_id)

tool_progress_bp = Blueprint("tool_progress", __name__, url_prefix="/api/tools")


@tool_progress_bp.get("/overview")
@jwt_required()
def overview():
    uid = get_jwt_identity()
    rows = db.session.execute(
        """
        SELECT DISTINCT ON (tool, user_id)
               id, tool, user_id, percentage, status, created_at
        FROM progress
        WHERE user_id = :uid
        ORDER BY tool, user_id, created_at DESC
        """,
        {"uid": uid},
    ).mappings().all()

    items = []
    for r in rows:
        items.append(
            {
                "tool": r["tool"],
                "percentage": r["percentage"] or 0,
                "status": r["status"],
                "updated_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
        )
    return jsonify({"items": items})