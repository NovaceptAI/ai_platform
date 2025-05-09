from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from .timeline_builder import (
    generate_timeline_from_category,
    generate_timeline_from_document,
    generate_timeline_from_text
)
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Blueprint setup
timeline_builder_bp = Blueprint('timeline_builder', __name__)
UPLOAD_FOLDER = '/tmp'

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to handle file uploads
def handle_file_upload(file):
    """Handles file uploads and saves the file to a temporary location."""
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    logger.info(f"File saved to temporary path: {file_path}")
    return file_path

# Route for generating a historical timeline
@timeline_builder_bp.route('/generate_timeline', methods=['POST'])
def generate_timeline():
    try:
        if 'multipart/form-data' in request.content_type:
            # Handle document-based input
            file = request.files.get('file')
            if not file:
                return jsonify({"error": "File is required"}), 400

            file_path = handle_file_upload(file)
            try:
                timeline = generate_timeline_from_document(file_path)
            finally:
                os.remove(file_path)
            return jsonify(timeline)

        elif 'application/json' in request.content_type:
            # Handle text or category-based input
            data = request.get_json()
            method = data.get('method')

            if method == 'category':
                category = data.get('category')
                if not category:
                    return jsonify({"error": "Category is required"}), 400
                timeline = generate_timeline_from_category(category)

            elif method == 'text':
                text = data.get('text')
                if not text:
                    return jsonify({"error": "Text is required"}), 400
                timeline = generate_timeline_from_text(text)

            else:
                return jsonify({"error": "Invalid method"}), 400

            return jsonify(timeline)

        else:
            return jsonify({"error": "Unsupported Content-Type"}), 415

    except Exception as e:
        logger.error(f"Error generating timeline: {str(e)}")
        return jsonify({"error": str(e)}), 500