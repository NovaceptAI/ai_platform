from flask import Blueprint, request, jsonify
from .quiz_creator import generate_mcq_question, generate_quiz, analyze_document_and_generate_quiz
from werkzeug.utils import secure_filename
import os

quiz_creator_bp = Blueprint('quiz_creator', __name__)
UPLOAD_FOLDER = 'tmp'  # Adjust the path as needed

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@quiz_creator_bp.route('/generate_question', methods=['POST'])
def generate_question():
    data = request.get_json()
    category = data.get('category', '')
    if not category:
        return jsonify({"error": "No category provided"}), 400

    question = generate_mcq_question(category)
    return jsonify({"question": question})

@quiz_creator_bp.route('/generate_quiz', methods=['POST'])
def generate_quiz_route():
    data = request.get_json()
    categories = data.get('categories', [])
    num_questions = data.get('num_questions', 0)
    if not categories or not num_questions:
        return jsonify({"error": "Categories or number of questions not provided"}), 400

    quiz = generate_quiz(categories, num_questions)
    return jsonify({"quiz": quiz})

@quiz_creator_bp.route('/analyze_document_and_generate_quiz', methods=['POST'])
def analyze_document_and_generate_quiz_route():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    file_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(file_path)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            document_text = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            document_text = f.read()

    num_questions = int(request.form.get('num_questions', 0))
    if num_questions <= 0:
        return jsonify({"error": "Invalid number of questions provided"}), 400

    try:
        quiz = analyze_document_and_generate_quiz(document_text, num_questions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.remove(file_path)

    return jsonify({"quiz": quiz})