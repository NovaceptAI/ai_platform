from flask import Blueprint, request, jsonify
from .summarizer import Summarizer
import os
import logging

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
    if 'file' not in request.files:
        logger.info("No file provided in the request")
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    file_path = f"/tmp/{file.filename}"
    file.save(file_path)
    logger.info(f"File saved to temporary path: {file_path}")

    try:
        summary_data = summarizer._summarize_file(file_path)
        logger.info("File summarization completed successfully")
    except ValueError as e:
        logger.error(f"Error during file summarization: {e}")
        return jsonify({"error": str(e)}), 400
    finally:
        os.remove(file_path)
        logger.info(f"Temporary file removed: {file_path}")

    return jsonify(summary_data)

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