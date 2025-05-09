from flask import Blueprint, request, jsonify
from .document_analyzer import analyze_document, analyze_text
from werkzeug.utils import secure_filename
import os

document_analyzer_bp = Blueprint('document_analyzer', __name__)
UPLOAD_FOLDER = 'tmp'  # Adjust the path as needed

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@document_analyzer_bp.route('/analyze', methods=['POST'])
def analyze():
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            file.save(file_path)
        except Exception as e:
            return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

        analysis = analyze_document(file_path)
        return jsonify(analysis)
    elif 'text' in request.form:
        text = request.form['text']
        analysis = analyze_text(text)
        return jsonify(analysis)
    else:
        return jsonify({"error": "No file or text provided"}), 400