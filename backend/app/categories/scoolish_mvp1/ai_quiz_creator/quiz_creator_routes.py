from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from .quiz_creator import generate_quiz_from_document, generate_quiz_from_category
import os
import logging
import tempfile
import json

# Configure logging
logger = logging.getLogger(__name__)

# Blueprint setup
quiz_creator_bp = Blueprint('quiz_creator', __name__)
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

# Factory function for quiz generation
def generate_quiz(method, data):
    """Generates a quiz based on the specified method and ensures the required number of questions."""
    num_questions = int(data.get('num_questions', 5))
    temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.json')
    temp_file_path = temp_file.name

    try:
        # Initialize an empty list to store questions
        all_questions = []

        while len(all_questions) < num_questions:
            remaining_questions = num_questions - len(all_questions)

            if method == 'category':
                category = data.get('category')
                raw_quiz = generate_quiz_from_category(category, remaining_questions)
            elif method == 'document':
                file_path = data.get('file_path')
                raw_quiz = generate_quiz_from_document(file_path, remaining_questions)
            else:
                raise ValueError("Invalid quiz generation method")

            # Format the raw quiz response
            new_questions = format_quiz_response(raw_quiz)

            # Add the new questions to the list
            all_questions.extend(new_questions)

            # Save the current questions to the temp file
            temp_file.seek(0)
            temp_file.write(json.dumps(all_questions))
            temp_file.truncate()

            # Log progress
            logger.info(f"Generated {len(all_questions)} questions so far. {remaining_questions} remaining.")

        # Return the final list of questions
        return all_questions

    finally:
        # Clean up the temporary file
        temp_file.close()
        os.remove(temp_file_path)

# Route for generating quizzes
@quiz_creator_bp.route('/generate_quiz', methods=['POST'])
def generate_quiz_route():
    try:
        # Handle multipart/form-data (for document-based quiz generation)
        if 'multipart/form-data' in request.content_type:
            file = request.files.get('file')
            method = request.form.get('method')
            num_questions = request.form.get('num_questions', 5)

            # Validate inputs
            is_valid, error_message = validate_request(
                {"file": file, "method": method, "num_questions": num_questions},
                required_fields=["file", "method", "num_questions"]
            )
            if not is_valid:
                logger.error(error_message)
                return jsonify({"error": error_message}), 400

            # Handle file upload
            file_path = handle_file_upload(file)

            # Generate quiz
            try:
                quiz_data = generate_quiz(method, {"file_path": file_path, "num_questions": num_questions})
            finally:
                os.remove(file_path)
                logger.info(f"Temporary file removed: {file_path}")

            return jsonify(quiz_data)

        # Handle application/json (for category-based quiz generation)
        elif 'application/json' in request.content_type:
            data = request.get_json()
            method = data.get('method')

            # Validate inputs
            is_valid, error_message = validate_request(
                data, required_fields=["method", "category", "num_questions"]
            )
            if not is_valid:
                logger.error(error_message)
                return jsonify({"error": error_message}), 400

            # Generate quiz
            quiz_data = generate_quiz(method, data)
            return jsonify(quiz_data)

        else:
            logger.error("Unsupported Content-Type")
            return jsonify({"error": "Unsupported Content-Type"}), 415

    except Exception as e:
        logger.error(f"Error generating quiz: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Helper function to format quiz response
def format_quiz_response(raw_quiz):
    """Formats the raw quiz response into a structured format."""
    logger.info(f"The Quiz response is: {raw_quiz}")
    questions = []

    # Split the raw quiz into individual question blocks
    for question_block in raw_quiz.strip().split("\n\n---\n\n"):
        lines = question_block.strip().split("\n")

        try:
            # Extract the question
            question_line = lines[0].replace("**Question", "").replace(":**", "").strip()
            question_text = lines[1].strip()

            # Extract the options
            options = {}
            for line in lines[2:6]:  # Options are in lines 2 to 5
                key, value = line.split(")", 1)
                options[key.strip()] = value.strip()

            # Extract the correct answer
            correct_answer_line = lines[6].replace("**Answer:**", "").strip()

            # Append the formatted question to the list
            questions.append({
                "question": f"Question {question_line}: {question_text}",
                "options": options,
                "correct_answer": correct_answer_line
            })

        except Exception as e:
            logger.error(f"Error processing question block: {question_block}. Error: {e}")
            continue

    return questions