import tempfile, uuid, os
# upload.py
from flask import Blueprint, request, jsonify, has_request_context
from azure.storage.blob import BlobServiceClient, ContentSettings
from werkzeug.utils import secure_filename
from datetime import datetime
from app.services.file_service import save_uploaded_file_metadata
from app.utils.hash_utils import calculate_sha256
from app.models.files import UploadedFile
from app.db import db
import logging
from urllib.parse import urlparse
from flask_jwt_extended import jwt_required, get_jwt_identity

upload_bp = Blueprint('upload', __name__)

# Azure config
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

logger = logging.getLogger(__name__)
CONTAINER_NAME = "scoolish"

def get_blob_service_client():
    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is not set")
    return BlobServiceClient.from_connection_string(conn)

def get_current_user_id():
    # Replace with actual auth logic
    return "admin"

@upload_bp.route('/upload', methods=['POST'])
@jwt_required()  # Ensure user is authenticated
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    user_id = get_jwt_identity()
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique_filename = f"{timestamp}_{uuid.uuid4().hex}_{filename}"
    blob_path = f"{user_id}/uploads/{unique_filename}"

     # 👉 Calculate hash
    file_hash = calculate_sha256(file)

    # Check for duplicate
    existing_file = UploadedFile.query.filter_by(hash=file_hash).first()
    if existing_file:
        bs = get_blob_service_client()
        return jsonify({
            'message': 'File already uploaded previously',
            'file_url': f"https://{bs.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{existing_file.file_path}",
            'file_name': existing_file.original_file_name,
            'stored_as': existing_file.file_path.split('/')[-1]
        }), 200
    
    # 👉 Save metadata (including hash)
    new_file = save_uploaded_file_metadata(
    user_id=user_id,  # ✅ Add this
    original_file_name=filename,
    blob_path=blob_path,
    file_type=file.content_type,
    file_hash=file_hash
)

    try:
        blob_client = get_blob_service_client().get_blob_client(container=CONTAINER_NAME, blob=blob_path)
        content_settings = ContentSettings(content_type=file.content_type)
        blob_client.upload_blob(file, overwrite=True, content_settings=content_settings)

        return jsonify({
            'message': 'File uploaded successfully',
            'file_url': blob_client.url,
            'original_name': filename,
            'stored_as': unique_filename
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@upload_bp.route('/files', methods=['GET'])
@jwt_required()
def list_files():
    user_id = get_jwt_identity()
    prefix = f"{user_id}/uploads/"

    try:
        # 1. Get all blobs from Azure
        container_client = get_blob_service_client().get_container_client(CONTAINER_NAME)
        blob_list = container_client.list_blobs(name_starts_with=prefix)

        # 2. Extract stored file names from Azure blob paths
        stored_file_names = [blob.name.split('/')[-1] for blob in blob_list]

        # 3. Fetch original_file_name for matching stored_file_names from DB
        uploaded_files = db.session.query(UploadedFile).filter(
            UploadedFile.stored_file_name.in_(stored_file_names)
        ).all()

        # 4. Return only original_file_name
        files = [
                    {
                        "name": file.original_file_name,
                        "stored_name": file.stored_file_name
                    }
                    for file in uploaded_files
                ]

        return jsonify({ "files": files })

    except Exception as e:
        return jsonify({ "error": str(e) }), 500


def download_blob_to_tmp(filename_or_url, user_id: str = None):
    # Extract stored filename safely
    parsed = urlparse(filename_or_url)
    stored_filename = os.path.basename(parsed.path) if parsed.scheme else filename_or_url

    # Resolve user_id from request JWT if available
    if user_id is None and has_request_context():
        try:
            user_id = get_jwt_identity()
        except Exception:
            user_id = None

    # Fallback: resolve user_id from DB by stored filename
    if not user_id:
        try:
            rec = UploadedFile.query.filter_by(stored_file_name=stored_filename).first()
            if rec:
                user_id = rec.user_id
        except Exception:
            pass

    if not user_id:
        raise RuntimeError("Unable to determine user_id for vault download")

    blob_path = f"{user_id}/uploads/{stored_filename}"

    bs = get_blob_service_client()
    blob_client = bs.get_blob_client(container=CONTAINER_NAME, blob=blob_path)

    tmp_path = os.path.join("/tmp", stored_filename)  # ✅ Only actual filename, no full URL
    logger.info(f"Downloading blob to temporary path: {tmp_path}")

    with open(tmp_path, "wb") as f:
        download_stream = blob_client.download_blob()
        f.write(download_stream.readall())
    return tmp_path