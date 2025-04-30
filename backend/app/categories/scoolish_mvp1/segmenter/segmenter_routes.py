from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
from .segmenter import segment_document, extract_keywords, summarize_document, named_entity_recognition, sentiment_analysis

segmenter_bp = Blueprint('segmenter', __name__)
UPLOAD_FOLDER = 'tmp'  # Adjust the path as needed

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_document_text():
    if 'file' in request.files:
        file = request.files['file']
        file_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        file.save(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                document_text = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                document_text = f.read()
        os.remove(file_path)
        return document_text
    else:
        data = request.get_json()
        return data.get('document_text', '')

@segmenter_bp.route('/segment_document', methods=['POST'])
def segment_document_route():
    document_text = get_document_text()
    if not document_text:
        return jsonify({"error": "No document text provided"}), 400

    segmented_document = segment_document(document_text)
    return jsonify({"segmented_document": segmented_document})

@segmenter_bp.route('/extract_keywords', methods=['POST'])
def extract_keywords_route():
    document_text = get_document_text()
    if not document_text:
        return jsonify({"error": "No document text provided"}), 400

    keywords = extract_keywords(document_text)
    return jsonify({"keywords": keywords})

@segmenter_bp.route('/summarize_document', methods=['POST'])
def summarize_document_route():
    document_text = get_document_text()
    if not document_text:
        return jsonify({"error": "No document text provided"}), 400

    summary = summarize_document(document_text)
    return jsonify({"summary": summary})

@segmenter_bp.route('/named_entity_recognition', methods=['POST'])
def named_entity_recognition_route():
    document_text = get_document_text()
    if not document_text:
        return jsonify({"error": "No document text provided"}), 400

    entities = named_entity_recognition(document_text)
    return jsonify({"entities": entities})

@segmenter_bp.route('/sentiment_analysis', methods=['POST'])
def sentiment_analysis_route():
    document_text = get_document_text()
    if not document_text:
        return jsonify({"error": "No document text provided"}), 400

    sentiment = sentiment_analysis(document_text)
    return jsonify({"sentiment": sentiment})