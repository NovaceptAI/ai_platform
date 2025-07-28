from flask import Blueprint, request, jsonify
from .summarizer import Summarizer
from app.tasks.summarizer_tasks import summarize_page
import os
import logging
import tempfile
from app.routes.upload import download_blob_to_tmp
from app.db import db
from app.models import FilePage, UploadedFile
from uuid import uuid4
from app.utils.file_utils import extract_text_by_pages

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
def summarize_file_route():
    try:
        # 1. Extract the file from the request
        if request.is_json:
            data = request.get_json()
            filename = data.get('filename')
            from_vault = data.get('fromVault', False)

            if not filename or not from_vault:
                return jsonify({"error": "Missing filename or vault flag"}), 400

            file_path = download_blob_to_tmp(filename)
        elif 'file' in request.files:
            file = request.files['file']
            file_path = os.path.join(tempfile.gettempdir(), file.filename)
            file.save(file_path)
        else:
            return jsonify({"error": "No valid file provided"}), 400

        # 2. Lookup uploaded file from DB
        uploaded_file = db.session.query(UploadedFile).filter_by(stored_file_name=filename).first()
        if not uploaded_file:
            return jsonify({"error": "Uploaded file not found in DB"}), 404


        # Check if file pages already exist
        existing_pages = db.session.query(FilePage).filter_by(file_id=uploaded_file.id).all()

        if existing_pages:
            # Reuse existing pages (no need to extract or save again)
            for page in existing_pages:
                summarize_page.delay(str(page.id))
        else:
            # Extract pages from file
            pages = extract_text_by_pages(file_path)
            uploaded_file.total_pages = len(pages)
            db.session.commit()

            # Save each page + enqueue task
            for i, page_text in enumerate(pages, start=1):
                file_page = FilePage(
                    id=uuid4(),
                    file_id=uploaded_file.id,
                    page_number=i,
                    page_text=page_text
                )
                db.session.add(file_page)
                db.session.flush()
                summarize_page.delay(str(file_page.id))

            db.session.commit()
        return jsonify({"message": f"Processing {len(pages)} pages in background", "file_id": str(uploaded_file.id)})

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