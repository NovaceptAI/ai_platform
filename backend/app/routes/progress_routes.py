from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import Progress, UploadedFile

progress_bp = Blueprint('progress', __name__, url_prefix='/api/progress')

@progress_bp.route('/<uuid:progress_id>', methods=['GET'])
@jwt_required()
def get_progress(progress_id):
    """Get progress for a specific progress_id"""
    try:
        user_id = get_jwt_identity()
        
        # Get the specific progress record
        progress = db.session.query(Progress).filter(
            Progress.id == progress_id,
            Progress.user_id == user_id
        ).first()
        
        if not progress:
            return jsonify({"error": "Progress not found"}), 404
            
        # Get original filename if available
        file_name = "Unknown"
        if progress.file_id:
            uploaded_file = db.session.query(UploadedFile).filter(
                UploadedFile.id == progress.file_id,
                UploadedFile.user_id == user_id
            ).first()
            if uploaded_file:
                file_name = uploaded_file.original_file_name
        
        return jsonify({
            "id": str(progress.id),
            "file_id": str(progress.file_id) if progress.file_id else None,
            "original_name": file_name,
            "tool": progress.tool,
            "status": progress.status,
            "percentage": progress.percentage,
            "created_at": progress.created_at.isoformat() if progress.created_at else None,
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None,
            "error_message": progress.error_message
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

@progress_bp.route('/<stage>', methods=['GET'])
@jwt_required()
def get_stage_progress(stage):
    """Get progress for a specific learning path stage"""
    try:
        user_id = get_jwt_identity()
        
        if stage not in ['discover','organize','mastery','create','collaborate']:
            return jsonify({'error':'Invalid stage'}), 400
        
        # Get all progress records for this stage
        progress_records = db.session.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.tool.like(f'learning_path:{stage}%')
        ).order_by(Progress.created_at.desc()).all()
        
        if not progress_records:
            return jsonify({
                "stage": stage,
                "status": "not_started",
                "progress_records": [],
                "summary": {
                    "total_tasks": 0,
                    "completed_tasks": 0,
                    "in_progress_tasks": 0,
                    "failed_tasks": 0
                }
            }), 200
        
        # Format progress records
        formatted_records = []
        for progress in progress_records:
            formatted_records.append({
                "id": str(progress.id),
                "tool": progress.tool,
                "status": progress.status,
                "percentage": progress.percentage,
                "created_at": progress.created_at.isoformat() if progress.created_at else None,
                "updated_at": progress.updated_at.isoformat() if progress.updated_at else None,
                "error_message": progress.error_message
            })
        
        # Calculate summary
        total_tasks = len(progress_records)
        completed_tasks = len([p for p in progress_records if p.status == 'completed'])
        in_progress_tasks = len([p for p in progress_records if p.status == 'in_progress'])
        failed_tasks = len([p for p in progress_records if p.status == 'failed'])
        
        overall_status = "completed" if completed_tasks == total_tasks else \
                        "in_progress" if in_progress_tasks > 0 else \
                        "failed" if failed_tasks > 0 else "not_started"
        
        return jsonify({
            "stage": stage,
            "status": overall_status,
            "progress_records": formatted_records,
            "summary": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "in_progress_tasks": in_progress_tasks,
                "failed_tasks": failed_tasks,
                "completion_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500