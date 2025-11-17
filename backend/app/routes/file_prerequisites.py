"""
General file prerequisites checker
Used by tools to verify if files have required preprocessing data
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.files import UploadedFile, FilePage
from app.db import db
from sqlalchemy import and_, func
import logging

logger = logging.getLogger(__name__)

file_prerequisites_bp = Blueprint('file_prerequisites', __name__)


def check_file_has_summary(file_id: str) -> bool:
    """Check if file has page summaries"""
    try:
        # Check if any page has a summary
        summary_count = db.session.query(func.count(FilePage.id)).filter(
            and_(
                FilePage.file_id == file_id,
                FilePage.page_summary.isnot(None),
                FilePage.page_summary != ''
            )
        ).scalar()

        return summary_count > 0
    except Exception as e:
        logger.error(f"Error checking summary for file {file_id}: {e}")
        return False


def check_file_has_topics(file_id: str) -> bool:
    """Check if file has topic extraction data"""
    try:
        # Import here to avoid circular imports
        from app.models.analysis_results import TopicModelResult

        # Check if there's an active topic record
        topic = db.session.query(TopicModelResult).filter(
            and_(
                TopicModelResult.file_id == file_id,
                TopicModelResult.is_active == True
            )
        ).first()

        return topic is not None and topic.topics is not None
    except Exception as e:
        logger.error(f"Error checking topics for file {file_id}: {e}")
        return False


def check_file_has_analysis(file_id: str) -> bool:
    """Check if file has document analysis data"""
    try:
        # Import here to avoid circular imports
        from app.models.analysis_results import DocumentAnalysisResult

        # Check if there's an active analysis record
        analysis = db.session.query(DocumentAnalysisResult).filter(
            and_(
                DocumentAnalysisResult.file_id == file_id,
                DocumentAnalysisResult.is_active == True
            )
        ).first()

        return analysis is not None and analysis.entities is not None
    except Exception as e:
        logger.error(f"Error checking analysis for file {file_id}: {e}")
        return False


@file_prerequisites_bp.route('/check_prerequisites', methods=['POST'])
@jwt_required()
def check_prerequisites():
    """
    Check which preprocessing steps are complete for given files.

    Request body:
    {
        "file_ids": ["uuid1", "uuid2", ...],
        "required": ["summary", "topics", "analysis"]  # optional, defaults to all
    }

    Response:
    {
        "ready_files": ["uuid1"],
        "needs_preprocessing": [
            {
                "file_id": "uuid2",
                "file_name": "document.pdf",
                "missing": ["topics", "analysis"]
            }
        ]
    }
    """
    try:
        data = request.get_json()
        file_ids = data.get('file_ids', [])
        required = data.get('required', ['summary', 'topics', 'analysis'])

        if not file_ids:
            return jsonify({'error': 'file_ids required'}), 400

        user_id = get_jwt_identity()

        ready_files = []
        needs_preprocessing = []

        # Check prerequisites for each file
        for file_id in file_ids:
            # Verify file exists and belongs to user
            file_record = UploadedFile.query.filter_by(
                id=file_id,
                user_id=user_id
            ).first()

            if not file_record:
                logger.warning(f"File {file_id} not found or doesn't belong to user {user_id}")
                continue

            missing = []

            # Check each required prerequisite
            if 'summary' in required and not check_file_has_summary(file_id):
                missing.append('summary')

            if 'topics' in required and not check_file_has_topics(file_id):
                missing.append('topics')

            if 'analysis' in required and not check_file_has_analysis(file_id):
                missing.append('analysis')

            # Categorize file
            if missing:
                needs_preprocessing.append({
                    'file_id': str(file_id),
                    'file_name': file_record.original_file_name,
                    'stored_name': file_record.stored_file_name,
                    'missing': missing
                })
            else:
                ready_files.append(str(file_id))

        return jsonify({
            'ready_files': ready_files,
            'needs_preprocessing': needs_preprocessing
        }), 200

    except Exception as e:
        logger.error(f"Error checking prerequisites: {e}")
        return jsonify({'error': str(e)}), 500
