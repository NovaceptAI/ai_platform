from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import Progress, UploadedFile

progress_bp = Blueprint('progress', __name__, url_prefix='/api/progress')

@progress_bp.route('/all', methods=['GET'])
@jwt_required()
def get_all_progress():
    try:
        user_id = get_jwt_identity()

        # Get all in-progress tasks across all tools for this user
        tasks = db.session.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.status == 'in_progress'
        ).all()

        # Fetch original filenames for display
        file_ids = list({task.file_id for task in tasks})
        uploaded_files = db.session.query(UploadedFile).filter(
            UploadedFile.user_id == user_id,
            UploadedFile.id.in_(file_ids)
        ).all()
        file_name_map = {file.id: file.original_file_name for file in uploaded_files}

        # Format result
        results = []
        for task in tasks:
            results.append({
                "progress_id": task.id,
                "file_id": task.file_id,
                "original_name": file_name_map.get(task.file_id, "Unknown"),
                "tool": task.tool,
                "status": task.status,
                "percentage": task.percentage
            })

        return jsonify(results), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500