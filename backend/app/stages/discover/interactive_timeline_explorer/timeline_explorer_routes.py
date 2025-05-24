from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from .timeline_explorer import (
    generate_timeline_from_category,
    generate_timeline_from_document,
    generate_timeline_from_text
)
from routes.upload import download_blob_to_tmp  # <- Make sure you have this or import correctly
import os
import logging
import tempfile

# Configure logging
logger = logging.getLogger(__name__)

# Blueprint setup
timeline_explorer_bp = Blueprint('timeline_explorer', __name__)
UPLOAD_FOLDER = '/tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def handle_file_upload(file):
    """Handles file uploads and saves the file to a temporary location."""
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    logger.info(f"File saved to temporary path: {file_path}")
    return file_path

@timeline_explorer_bp.route('/generate_timeline', methods=['POST'])
def generate_timeline():
    file_path = None

    try:
        if request.is_json:
            data = request.get_json()
            method = data.get('method')

            # Vault-based document input
            if method == 'document':
                filename = data.get('filename')
                from_vault = data.get('fromVault', False)

                if from_vault:
                    if not filename:
                        logger.info("Missing filename for vault-based timeline generation")
                        return jsonify({"error": "Missing filename for vault-based timeline generation"}), 400

                    file_path = download_blob_to_tmp(filename)
                    logger.info(f"Vault file downloaded to: {file_path}")
                else:
                    logger.info("Expected file upload or fromVault=True in JSON")
                    return jsonify({"error": "Invalid request: missing file or vault parameters"}), 400

                timeline = generate_timeline_from_document(file_path)
                return jsonify(timeline)

            elif method == 'category':
                category = data.get('category')
                if not category:
                    return jsonify({"error": "Category is required"}), 400
                timeline = generate_timeline_from_category(category)
                logger.info(f"Generated timeline for category: {category}")
                return jsonify(timeline)

            elif method == 'text':
                text = data.get('text')
                if not text:
                    return jsonify({"error": "Text is required"}), 400
                timeline = generate_timeline_from_text(text)
                return jsonify(timeline)

            else:
                return jsonify({"error": "Invalid method"}), 400

        elif 'multipart/form-data' in request.content_type:
            file = request.files.get('file')
            if not file:
                return jsonify({"error": "File is required"}), 400

            file_path = handle_file_upload(file)
            timeline = generate_timeline_from_document(file_path)
            return jsonify(timeline)

        else:
            return jsonify({"error": "Unsupported Content-Type"}), 415

    except Exception as e:
        logger.error(f"Error generating timeline: {str(e)}")
        return jsonify({"error": str(e)}), 500

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Temporary file removed: {file_path}")