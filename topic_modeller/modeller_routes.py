from flask import Blueprint, request, jsonify
from .topic_modeller import extract_topics, extract_keywords, cluster_documents, visualize_topics, summarize_topics, named_entity_recognition, sentiment_analysis, analyze_topic_trends

modeller_bp = Blueprint('modeller', __name__)

@modeller_bp.route('/extract_topics', methods=['POST'])
def extract_topics_route():
    data = request.get_json()
    document_text = data.get('document_text', '')
    if not document_text:
        return jsonify({"error": "No document text provided"}), 400

    topics = extract_topics(document_text)
    return jsonify({"topics": topics})

@modeller_bp.route('/extract_keywords', methods=['POST'])
def extract_keywords_route():
    data = request.get_json()
    document_text = data.get('document_text', '')
    if not document_text:
        return jsonify({"error": "No document text provided"}), 400

    keywords = extract_keywords(document_text)
    return jsonify({"keywords": keywords})

@modeller_bp.route('/cluster_documents', methods=['POST'])
def cluster_documents_route():
    data = request.get_json()
    documents = data.get('documents', [])
    if not documents:
        return jsonify({"error": "No documents provided"}), 400

    clusters = cluster_documents(documents)
    return jsonify({"clusters": clusters})

@modeller_bp.route('/visualize_topics', methods=['POST'])
def visualize_topics_route():
    data = request.get_json()
    document_text = data.get('document_text', '')
    if not document_text:
        return jsonify({"error": "No document text provided"}), 400

    visualization = visualize_topics(document_text)
    return jsonify({"visualization": visualization})

@modeller_bp.route('/summarize_topics', methods=['POST'])
def summarize_topics_route():
    data = request.get_json()
    document_text = data.get('document_text', '')
    if not document_text:
        return jsonify({"error": "No document text provided"}), 400

    summary = summarize_topics(document_text)
    return jsonify({"summary": summary})

@modeller_bp.route('/named_entity_recognition', methods=['POST'])
def named_entity_recognition_route():
    data = request.get_json()
    document_text = data.get('document_text', '')
    if not document_text:
        return jsonify({"error": "No document text provided"}), 400

    entities = named_entity_recognition(document_text)
    return jsonify({"entities": entities})

@modeller_bp.route('/sentiment_analysis', methods=['POST'])
def sentiment_analysis_route():
    data = request.get_json()
    document_text = data.get('document_text', '')
    if not document_text:
        return jsonify({"error": "No document text provided"}), 400

    sentiment = sentiment_analysis(document_text)
    return jsonify({"sentiment": sentiment})

@modeller_bp.route('/analyze_topic_trends', methods=['POST'])
def analyze_topic_trends_route():
    data = request.get_json()
    documents = data.get('documents', [])
    if not documents:
        return jsonify({"error": "No documents provided"}), 400

    trends = analyze_topic_trends(documents)
    return jsonify({"trends": trends})