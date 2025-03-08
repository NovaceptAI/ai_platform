from flask import Blueprint, request, jsonify
from .quiz_creator import generate_mcq_question, generate_quiz

quiz_creator_bp = Blueprint('quiz_creator', __name__)

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