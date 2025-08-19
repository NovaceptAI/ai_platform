from flask import Blueprint, request, jsonify
from .chrono_ai import analyze_document, analyze_file
import os
import logging

logger = logging.getLogger(__name__)

chrono_ai_bp = Blueprint('chrono_ai', __name__)

@chrono_ai_bp.route('/extract_chronology_from_text', methods=['POST'])
def extract_chronology_from_text():
    """
    Analyzes raw document text and extracts events in chronological order.
    """
    logger.info("Received request to extract chronology from raw text.")
    data = request.get_json()
    document_text = data.get('document_text', '')
    if not document_text:
        logger.warning("No document text provided in the request.")
        return jsonify({"error": "No document text provided"}), 400

    try:
        logger.info("Analyzing document text...")
        events = analyze_document(document_text)
        logger.info("Successfully extracted chronology from text.")
        return jsonify({"events": events})
    except Exception as e:
        logger.error(f"Error analyzing document text: {e}")
        return jsonify({"error": str(e)}), 500

@chrono_ai_bp.route('/extract_chronology_from_file', methods=['POST'])
def extract_chronology_from_file():
    """
    Analyzes an uploaded document file and extracts events in chronological order.
    """
    logger.info("Received request to extract chronology from uploaded file.")
    if 'file' not in request.files:
        logger.warning("No file provided in the request.")
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    file_path = f"/tmp/{file.filename}"
    logger.info(f"Saving uploaded file to temporary path: {file_path}")
    file.save(file_path)  # Save the uploaded file to a temporary location

    try:
        logger.info("Analyzing file...")
        events = analyze_file(file_path)
        logger.info("Successfully extracted chronology from file.")
        os.remove(file_path)  # Clean up the temporary file
        logger.info(f"Temporary file removed: {file_path}")
        return jsonify({"events": events})
    except Exception as e:
        logger.error(f"Error analyzing file: {e}")
        os.remove(file_path)  # Ensure the temporary file is removed in case of an error
        logger.info(f"Temporary file removed after error: {file_path}")
        return jsonify({"error": str(e)}), 500