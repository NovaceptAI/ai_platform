from flask import Blueprint, request, jsonify
from .summarizer import Summarizer
from app.tasks.summarizer_tasks import summarize_page_batch
import os
import logging
import tempfile
from app.routes.upload import download_blob_to_tmp
from app.db import db
from app.models import FilePage, UploadedFile
from uuid import uuid4
from app.utils.file_utils import extract_text_by_pages
from math import ceil
from app.models import Progress
from flask_jwt_extended import jwt_required, get_jwt_identity


# Configure logger
logger = logging.getLogger(__name__)
# logger.info("This is a log message from a blueprint.")

summarizer_bp = Blueprint('summarizer', __name__)
# Create an instance of the Summarizer class
summarizer = Summarizer()

@summarizer_bp.route('/summarize_text', methods=['POST'])
def summarize_text_route():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        logger.info("No text provided in the request")
        return jsonify({"error": "No text provided"}), 400

    logger.info("Received text for summarization")
    summary_data = summarizer._summarize_text(text)
    logger.info("Text summarization completed successfully")
    return jsonify(summary_data)


@summarizer_bp.route('/summarize_file', methods=['POST'])
@jwt_required()
def summarize_file_route():
    try:
        # 1. Extract file
        if request.is_json:
            data = request.get_json()
            filename = data.get('filename')
            logger.info(f"Received filename: {filename}")
            from_vault = data.get('fromVault', False)
            if not filename or not from_vault:
                return jsonify({"error": "Missing filename or vault flag"}), 400
            file_path = download_blob_to_tmp(filename, user_id=get_jwt_identity())

        elif 'file' in request.files:
            file = request.files['file']
            file_path = os.path.join(tempfile.gettempdir(), file.filename)
            file.save(file_path)

        else:
            return jsonify({"error": "No valid file provided"}), 400


        # 2. DB lookup
        uploaded_file = db.session.query(UploadedFile).filter_by(stored_file_name=filename).first()
        if not uploaded_file:
            return jsonify({"error": "Uploaded file not found in DB"}), 404

        # 3. Create progress tracker
        progress = Progress(
            id=uuid4(),
            user_id=uploaded_file.user_id,
            file_id=uploaded_file.id,
            status='in_progress',
            tool='summarizer',
        )
        db.session.add(progress)
        db.session.commit()

        existing_pages = db.session.query(FilePage).filter_by(file_id=uploaded_file.id).all()
        processed_pages = []

        if existing_pages:
            for chunk in chunk_list(existing_pages, 5):
                valid_ids = [str(p.id) for p in chunk if p.page_text and not p.page_summary]
                if valid_ids:
                    summarize_page_batch.delay(valid_ids)
            processed_pages = existing_pages

        else:
            pages = extract_text_by_pages(file_path)
            pages = [p for p in pages if p.strip()]  # Skip empty
            uploaded_file.total_pages = len(pages)
            db.session.commit()

            new_pages = []
            for i, page_text in enumerate(pages, start=1):
                file_page = FilePage(
                    id=uuid4(),
                    file_id=uploaded_file.id,
                    page_number=i,
                    page_text=page_text
                )
                db.session.add(file_page)
                db.session.flush()
                new_pages.append(file_page)
                processed_pages.append(file_page)

            db.session.commit()

            for chunk in chunk_list(new_pages, 5):
                page_ids = [str(p.id) for p in chunk if p.page_text]
                summarize_page_batch.delay(page_ids)

        return jsonify({
            "message": f"Processing {len(processed_pages)} pages in background",
            "file_id": str(uploaded_file.id),
            "progress_id": str(progress.id)
        })

    except Exception as e:
        db.session.rollback()
        logger.exception("Summarization route failed")
        return jsonify({"error": "Internal server error"}), 500



@summarizer_bp.route('/export_segments', methods=['POST'])
def export_segments_route():
    data = request.get_json()
    segments = data.get('segments', [])
    format = data.get('format', 'json')
    
    if not segments:
        logger.info("No segments provided in the request")
        return jsonify({"error": "No segments provided"}), 400

    logger.info(f"Exporting segments in {format} format")
    try:
        exported_data = summarizer._export_segments(segments, format)
        logger.info("Segments exported successfully")
    except ValueError as e:
        logger.error(f"Error during segment export: {e}")
        return jsonify({"error": str(e)}), 400

    return jsonify({"exported_data": exported_data})


# @summarizer_bp.route('/progress/<file_id>', methods=['GET'])
# def summarization_progress(file_id):
#     try:
#         uploaded_file = db.session.query(UploadedFile).filter_by(id=file_id).first()
#         if not uploaded_file:
#             return jsonify({"error": "File not found"}), 404

#         total_pages = uploaded_file.total_pages or 0
#         summarized_count = db.session.query(FilePage).filter(
#             FilePage.file_id == file_id,
#             FilePage.page_summary.isnot(None)
#         ).count()

#         return jsonify({
#             "file_id": str(file_id),
#             "total_pages": total_pages,
#             "pages_summarized": summarized_count,
#             "percentage": int((summarized_count / total_pages) * 100) if total_pages else 0
#         })

#     except Exception as e:
#         logger.exception("Error fetching progress")
#         return jsonify({"error": "Internal server error"}), 500


@summarizer_bp.route('/get_summary/<file_id>', methods=['GET'])
def get_summarized_file(file_id):
    try:
        pages = db.session.query(FilePage).filter_by(file_id=file_id).order_by(FilePage.page_number).all()
        if not pages:
            return jsonify({"error": "No pages found"}), 404

        response = {
            "file_id": file_id,
            "pages": [
                {
                    "page_number": page.page_number,
                    "summary": page.page_summary
                }
                for page in pages if page.page_summary
            ]
        }
        return jsonify(response)

    except Exception as e:
        logger.exception("Error fetching summary")
        return jsonify({"error": "Internal server error"}), 500


@summarizer_bp.route('/progress/<progress_id>', methods=['GET'])
def summarization_progress(progress_id):
    try:
        progress = db.session.query(Progress).filter_by(id=progress_id).first()
        if not progress:
            return jsonify({"error": "Progress ID not found"}), 404

        uploaded_file = db.session.query(UploadedFile).filter_by(id=progress.file_id).first()
        if not uploaded_file:
            return jsonify({"error": "File not found"}), 404

        total_pages = uploaded_file.total_pages or 0
        summarized_count = db.session.query(FilePage).filter(
            FilePage.file_id == uploaded_file.id,
            FilePage.page_summary.isnot(None)
        ).count()

        # Calculate percentage
        percentage = int((summarized_count / total_pages) * 100) if total_pages else 0

        # ✅ Update percentage and status in the DB if changed
        if progress.percentage != percentage:
            progress.percentage = percentage

        if total_pages > 0 and summarized_count == total_pages and progress.status != "done":
            progress.status = "done"

        db.session.commit()

        return jsonify({
            "progress_id": str(progress.id),
            "file_id": str(uploaded_file.id),
            "status": progress.status,
            "total_pages": total_pages,
            "pages_summarized": summarized_count,
            "percentage": percentage
        })

    except Exception as e:
        logger.exception("Error fetching progress")
        return jsonify({"error": "Internal server error"}), 500

def chunk_list(lst, chunk_size):
    """Utility to chunk list into groups of n."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]