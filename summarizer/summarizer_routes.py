from flask import Blueprint, request, jsonify
from .summarizer import summarize_text, summarize_file, export_segments
import os

summarizer_bp = Blueprint('summarizer', __name__)

@summarizer_bp.route('/summarize_text', methods=['POST'])
def summarize_text_route():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({"error": "No text provided"}), 400

    summary_data = summarize_text(text)
    return jsonify(summary_data)

@summarizer_bp.route('/summarize_file', methods=['POST'])
def summarize_file_route():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    file_path = f"/tmp/{file.filename}"
    file.save(file_path)

    try:
        summary_data = summarize_file(file_path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    finally:
        os.remove(file_path)

    return jsonify(summary_data)

@summarizer_bp.route('/export_segments', methods=['POST'])
def export_segments_route():
    data = request.get_json()
    segments = data.get('segments', [])
    format = data.get('format', 'json')
    
    if not segments:
        return jsonify({"error": "No segments provided"}), 400

    try:
        exported_data = export_segments(segments, format)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"exported_data": exported_data})