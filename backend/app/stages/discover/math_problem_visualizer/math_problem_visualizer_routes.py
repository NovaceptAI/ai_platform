from flask import Blueprint, request, jsonify
from .math_problem_visualizer import solve_and_visualize_math_problem
# from .utils import load_file_from_vault, extract_text_from_file  # You'll need to implement these
# /home/azureuser/ai_platform/backend/app/utils/file_utils.py 
import logging
from app.routes.upload import download_blob_to_tmp
from app.utils.file_utils import (
    detect_file_type,
    extract_text_from_document,
    extract_text_from_audio,
    extract_text_from_video
)
logger = logging.getLogger(__name__)
math_problem_visualiser_bp = Blueprint('math_problem_visualiser', __name__)

@math_problem_visualiser_bp.route('/visualize_math_problem', methods=['POST'])
def visualize_math_problem():
    """
    Handles visualization of math problems from:
    - direct problem input (JSON)
    - a filename from the Knowledge Vault
    - a file uploaded directly (PDF/DOCX/TXT)
    """
    try:
        problem_text = None

        # If JSON input with "problem"
        if request.is_json:
            data = request.get_json()
            logger.info(f"Received JSON data: {data}")
            problem_text = data.get('problem')

            # Optional: vault file support in JSON
            filename = data.get('filename')
            from_vault = data.get('fromVault', False)
            if from_vault and filename:
                logger.info(f"Fetching from vault: {filename}")
                filepath = download_blob_to_tmp(filename)
                problem_text = extract_text_from_document(filepath)

        # If multipart (file upload)
        elif 'multipart/form-data' in request.content_type:
            file = request.files.get('file')
            if file:
                logger.info(f"Processing uploaded file: {file.filename}")
                problem_text = extract_text_from_document(file)

        # Validate
        if not problem_text:
            return jsonify({"error": "No math problem or valid file provided."}), 400

        logger.info(f"Processing math problem: {problem_text}")
        result = solve_and_visualize_math_problem(problem_text)

        return jsonify({
            "solution": result["solution"],
            "steps": result["steps"],
            "visualization": result["visualization"]
        }), 200

    except ValueError as ve:
        logger.error(f"ValueError: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.exception("Unexpected error:")
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500