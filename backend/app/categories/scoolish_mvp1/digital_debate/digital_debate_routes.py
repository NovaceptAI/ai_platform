from flask import Blueprint, request, jsonify
from .digital_debate import create_debate, score_debate

digital_debate_bp = Blueprint('digital_debate', __name__)

@digital_debate_bp.route('/create_debate', methods=['POST'])
def create_debate_route():
    data = request.get_json()
    topic = data.get('topic', None)
    debate = create_debate(topic)
    return jsonify(debate)

@digital_debate_bp.route('/score_debate', methods=['POST'])
def score_debate_route():
    data = request.get_json()
    for_student_score = data.get('for_student_score', None)
    against_student_score = data.get('against_student_score', None)
    
    if for_student_score is None or against_student_score is None:
        return jsonify({"error": "Scores for both students must be provided"}), 400

    try:
        result = score_debate(for_student_score, against_student_score)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(result)