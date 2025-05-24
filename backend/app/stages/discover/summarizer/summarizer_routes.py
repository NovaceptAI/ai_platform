from flask import Blueprint, request, jsonify
from .summarizer import Summarizer
import os
import logging
import tempfile
from routes.upload import download_blob_to_tmp

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
    file_path = None

    try:
        if request.is_json:
            data = request.get_json()
            filename = data.get('filename')
            from_vault = data.get('fromVault', False)

            if from_vault:
                if not filename:
                    logger.info("Missing filename for vault-based summarization")
                    return jsonify({"error": "Missing filename for vault-based summarization"}), 400

                # Download file from Azure Blob Storage
                file_path = download_blob_to_tmp(filename)
                logger.info(f"Vault file downloaded to: {file_path}")
            else:
                logger.info("Expected file upload or fromVault=True in JSON")
                return jsonify({"error": "Invalid request: missing file or vault parameters"}), 400

        elif 'file' in request.files:
            file = request.files['file']
            file_path = os.path.join(tempfile.gettempdir(), file.filename)
            file.save(file_path)
            logger.info(f"Uploaded file saved to temporary path: {file_path}")
        else:
            logger.info("No file or valid JSON provided")
            return jsonify({"error": "No file or valid JSON payload provided"}), 400

        # Summarize
        summary_data = summarizer._summarize_file(file_path)
        logger.info("File summarization completed successfully")
        return jsonify(summary_data)

    except ValueError as e:
        logger.error(f"Error during file summarization: {e}")
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        logger.exception("Unexpected error")
        return jsonify({"error": "Internal server error"}), 500

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Temporary file removed: {file_path}")

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