from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from .homework_helper import (
    answer_question_from_category,
    answer_question_from_document,
    answer_question_from_text
)
import os
import logging
import tempfile

# Configure logging
logger = logging.getLogger(__name__)

# Blueprint setup
homework_helper_bp = Blueprint('homework_helper', __name__)
UPLOAD_FOLDER = '/tmp'

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to validate input
def validate_request(data, required_fields):
    """Validates that required fields are present in the request data."""
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    return True, None

# Helper function to handle file uploads
def handle_file_upload(file):
    """Handles file uploads and saves the file to a temporary location."""
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    logger.info(f"File saved to temporary path: {file_path}")
    return file_path

# Route for answering homework questions
@homework_helper_bp.route('/answer_question', methods=['POST'])
def answer_question_route():
    try:
        # Handle multipart/form-data (for document-based question answering)
        if 'multipart/form-data' in request.content_type:
            file = request.files.get('file')
            question = request.form.get('question')

            # Validate inputs
            is_valid, error_message = validate_request(
                {"file": file, "question": question},
                required_fields=["file", "question"]
            )
            if not is_valid:
                logger.error(error_message)
                return jsonify({"error": error_message}), 400

            # Handle file upload
            file_path = handle_file_upload(file)

            # Answer question
            try:
                answer = answer_question_from_document(file_path, question)
            finally:
                os.remove(file_path)
                logger.info(f"Temporary file removed: {file_path}")

            return jsonify({"answer": answer})

        # Handle application/json (for category-based or text-based question answering)
        elif 'application/json' in request.content_type:
            data = request.get_json()
            method = data.get('method')
            question = data.get('question')

            # Validate inputs
            if method == 'category':
                is_valid, error_message = validate_request(
                    data, required_fields=["method", "category", "question"]
                )
                if not is_valid:
                    logger.error(error_message)
                    return jsonify({"error": error_message}), 400

                # Answer question from category
                category = data.get('category')
                answer = answer_question_from_category(category, question)

            elif method == 'text':
                is_valid, error_message = validate_request(
                    data, required_fields=["method", "text", "question"]
                )
                if not is_valid:
                    logger.error(error_message)
                    return jsonify({"error": error_message}), 400

                # Answer question from text
                text = data.get('text')
                answer = answer_question_from_text(text, question)

            else:
                logger.error("Invalid method for question answering")
                return jsonify({"error": "Invalid method for question answering"}), 400

            return jsonify({"answer": answer})

        else:
            logger.error("Unsupported Content-Type")
            return jsonify({"error": "Unsupported Content-Type"}), 415

    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        return jsonify({"error": str(e)}), 500