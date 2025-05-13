from flask import Blueprint, request, jsonify
from azure.storage.blob import BlobServiceClient, ContentSettings
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import os

upload_bp = Blueprint('upload', __name__)

# Azure config
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "scoolish"
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

def get_current_user_id():
    # Replace with actual auth logic
    return "admin"

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    user_id = get_current_user_id()
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique_filename = f"{timestamp}_{uuid.uuid4().hex}_{filename}"
    blob_path = f"{user_id}/uploads/{unique_filename}"

    try:
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_path)
        content_settings = ContentSettings(content_type=file.content_type)
        blob_client.upload_blob(file, overwrite=True, content_settings=content_settings)

        return jsonify({
            'message': 'File uploaded successfully',
            'file_url': blob_client.url,
            'stored_as': unique_filename
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500