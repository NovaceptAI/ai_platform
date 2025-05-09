from flask import Blueprint, request, jsonify, current_app
from .topic_modeller import extract_topics_and_keywords_from_file, cluster_documents, visualize_topics, summarize_topics, named_entity_recognition, sentiment_analysis, analyze_topic_trends

modeller_bp = Blueprint('modeller', __name__)

# def get_document_text_or_path(data):
#     """Helper function to get document text or process uploaded file."""
#     if 'file' in request.files:
#         file = request.files['file']
#         file_path = f"/tmp/{file.filename}"  # Adjust the path as needed
#         file.save(file_path)
#         current_app.logger.info("Uploaded file saved to: %s", file_path)
#         return file_path
#     return data.get('document_text', '')

@modeller_bp.route('/extract_topics_keywords', methods=['POST'])
def extract_topics_route():
    if 'file' not in request.files:
        current_app.logger.error("No file provided in the request for /extract_topics_keywords")
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        current_app.logger.error("Empty filename provided for /extract_topics_keywords")
        return jsonify({"error": "No file selected"}), 400

    try:
        # Save the uploaded file to a temporary location
        file_path = f"/tmp/{file.filename}"  # Adjust the path as needed
        file.save(file_path)
        current_app.logger.info("Uploaded file saved to: %s", file_path)

        # Extract topics and keywords from the file
        result = extract_topics_and_keywords_from_file(file_path)
        current_app.logger.info("Extracted topics and keywords: %s", result)

        return jsonify(result)
    except Exception as e:
        current_app.logger.exception("Error processing file for /extract_topics_keywords")
        return jsonify({"error": "An error occurred while processing the file"}), 500

# @modeller_bp.route('/extract_keywords', methods=['POST'])
# def extract_keywords_route():
#     data = request.get_json()
#     current_app.logger.info("Received request for /extract_keywords with data: %s", data)
#     document_text_or_path = get_document_text_or_path(data)
#     if not document_text_or_path:
#         current_app.logger.error("No document text or file provided for /extract_keywords")
#         return jsonify({"error": "No document text or file provided"}), 400

#     keywords = extract_keywords(document_text_or_path)
#     current_app.logger.info("Extracted keywords: %s", keywords)
#     return jsonify({"keywords": keywords})

@modeller_bp.route('/cluster_documents', methods=['POST'])
def cluster_documents_route():
    data = request.get_json()
    current_app.logger.info("Received request for /cluster_documents with data: %s", data)
    documents = data.get('documents', [])
    if not documents:
        current_app.logger.error("No documents provided for /cluster_documents")
        return jsonify({"error": "No documents provided"}), 400

    clusters = cluster_documents(documents)
    current_app.logger.info("Generated clusters: %s", clusters)
    return jsonify({"clusters": clusters})

@modeller_bp.route('/visualize_topics', methods=['POST'])
def visualize_topics_route():
    data = request.get_json()
    current_app.logger.info("Received request for /visualize_topics with data: %s", data)
    document_text_or_path = get_document_text_or_path(data)
    if not document_text_or_path:
        current_app.logger.error("No document text or file provided for /visualize_topics")
        return jsonify({"error": "No document text or file provided"}), 400

    visualization = visualize_topics(document_text_or_path)
    current_app.logger.info("Generated visualization: %s", visualization)
    return jsonify({"visualization": visualization})

@modeller_bp.route('/summarize_topics', methods=['POST'])
def summarize_topics_route():
    data = request.get_json()
    current_app.logger.info("Received request for /summarize_topics with data: %s", data)
    document_text_or_path = get_document_text_or_path(data)
    if not document_text_or_path:
        current_app.logger.error("No document text or file provided for /summarize_topics")
        return jsonify({"error": "No document text or file provided"}), 400

    summary = summarize_topics(document_text_or_path)
    current_app.logger.info("Generated summary: %s", summary)
    return jsonify({"summary": summary})

@modeller_bp.route('/named_entity_recognition', methods=['POST'])
def named_entity_recognition_route():
    data = request.get_json()
    current_app.logger.info("Received request for /named_entity_recognition with data: %s", data)
    document_text_or_path = get_document_text_or_path(data)
    if not document_text_or_path:
        current_app.logger.error("No document text or file provided for /named_entity_recognition")
        return jsonify({"error": "No document text or file provided"}), 400

    entities = named_entity_recognition(document_text_or_path)
    current_app.logger.info("Extracted entities: %s", entities)
    return jsonify({"entities": entities})

@modeller_bp.route('/sentiment_analysis', methods=['POST'])
def sentiment_analysis_route():
    data = request.get_json()
    current_app.logger.info("Received request for /sentiment_analysis with data: %s", data)
    document_text_or_path = get_document_text_or_path(data)
    if not document_text_or_path:
        current_app.logger.error("No document text or file provided for /sentiment_analysis")
        return jsonify({"error": "No document text or file provided"}), 400

    sentiment = sentiment_analysis(document_text_or_path)
    current_app.logger.info("Analyzed sentiment: %s", sentiment)
    return jsonify({"sentiment": sentiment})

@modeller_bp.route('/analyze_topic_trends', methods=['POST'])
def analyze_topic_trends_route():
    data = request.get_json()
    current_app.logger.info("Received request for /analyze_topic_trends with data: %s", data)
    documents = data.get('documents', [])
    if not documents:
        current_app.logger.error("No documents provided for /analyze_topic_trends")
        return jsonify({"error": "No documents provided"}), 400

    trends = analyze_topic_trends(documents)
    current_app.logger.info("Analyzed topic trends: %s", trends)
    return jsonify({"trends": trends})