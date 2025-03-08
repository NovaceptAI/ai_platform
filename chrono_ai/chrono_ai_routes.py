from flask import Blueprint, request, jsonify
from .chrono_ai import analyze_document

chrono_ai_bp = Blueprint('chrono_ai', __name__)

@chrono_ai_bp.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    document_text = data.get('document_text', '')
    if not document_text:
        return jsonify({"error": "No document text provided"}), 400

    events = analyze_document(document_text)
    return jsonify({"events": events})