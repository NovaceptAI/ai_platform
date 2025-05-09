from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from .study_guide import (
    generate_study_guide_from_category,
    generate_study_guide_from_document,
    generate_study_guide_from_text
)
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Blueprint setup
study_guide_bp = Blueprint('study_guide', __name__)
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

# Route for generating a visual study guide
@study_guide_bp.route('/generate_visual_study_guide', methods=['POST'])
def generate_visual_study_guide():
    try:
        if 'multipart/form-data' in request.content_type:
            # Handle document-based input
            file = request.files.get('file')
            if not file:
                return jsonify({"error": "File is required"}), 400

            file_path = handle_file_upload(file)
            try:
                study_guide = generate_study_guide_from_document(file_path)
            finally:
                os.remove(file_path)
            return jsonify(study_guide)

        elif 'application/json' in request.content_type:
            # Handle text or category-based input
            data = request.get_json()
            method = data.get('method')

            if method == 'category':
                category = data.get('category')
                if not category:
                    return jsonify({"error": "Category is required"}), 400
                study_guide = generate_study_guide_from_category(category)

            elif method == 'text':
                text = data.get('text')
                if not text:
                    return jsonify({"error": "Text is required"}), 400
                study_guide = generate_study_guide_from_text(text)

            else:
                return jsonify({"error": "Invalid method"}), 400

            return jsonify(study_guide)

        else:
            return jsonify({"error": "Unsupported Content-Type"}), 415

    except Exception as e:
        logger.error(f"Error generating study guide: {str(e)}")
        return jsonify({"error": str(e)}), 500