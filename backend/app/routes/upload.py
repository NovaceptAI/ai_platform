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
    # Check for files in request
    files = []
    
    # Support both single file ('file') and multiple files ('files')
    if 'files' in request.files:
        files = request.files.getlist('files')
    elif 'file' in request.files:
        files = [request.files['file']]
    else:
        return jsonify({'error': 'No file part in request. Use "file" for single upload or "files" for multiple uploads'}), 400

    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No selected files'}), 400

    user_id = get_jwt_identity()
    results = []
    errors = []
    successful_uploads = 0
    
    for file in files:
        if file.filename == '':
            errors.append({
                'file': 'unnamed',
                'error': 'Empty filename'
            })
            continue
            
        try:
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            unique_filename = f"{timestamp}_{uuid.uuid4().hex}_{filename}"
            blob_path = f"{user_id}/uploads/{unique_filename}"

            # Calculate hash
            file_hash = calculate_sha256(file)

            # Check for duplicate within the same user's files
            existing_file = UploadedFile.query.filter_by(
                hash=file_hash,
                user_id=user_id
            ).first()
            if existing_file:
                bs = get_blob_service_client()
                results.append({
                    'original_name': filename,
                    'status': 'duplicate',
                    'message': 'File already uploaded previously',
                    'file_url': f"https://{bs.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{existing_file.file_path}",
                    'stored_as': existing_file.file_path.split('/')[-1],
                    'file_id': str(existing_file.id)  # Add file ID for duplicates too
                })
                continue
            
            # Save metadata (including hash)
            new_file = save_uploaded_file_metadata(
                user_id=user_id,
                original_file_name=filename,
                blob_path=blob_path,
                file_type=file.content_type,
                file_hash=file_hash
            )

            # Upload to Azure
            blob_client = get_blob_service_client().get_blob_client(container=CONTAINER_NAME, blob=blob_path)
            content_settings = ContentSettings(content_type=file.content_type)
            blob_client.upload_blob(file, overwrite=True, content_settings=content_settings)

            results.append({
                'original_name': filename,
                'status': 'success',
                'message': 'File uploaded successfully',
                'file_url': blob_client.url,
                'stored_as': unique_filename,
                'file_id': str(new_file.id)  # Add file ID to response
            })
            successful_uploads += 1

        except Exception as e:
            logger.error(f"Error uploading file {file.filename}: {str(e)}")
            errors.append({
                'file': file.filename,
                'error': str(e)
            })

    # Prepare response
    total_files = len(files)
    response_data = {
        'total_files': total_files,
        'successful_uploads': successful_uploads,
        'failed_uploads': len(errors),
        'results': results
    }
    
    if errors:
        response_data['errors'] = errors
    
    # Return appropriate status code
    if successful_uploads == 0:
        return jsonify(response_data), 400
    elif errors:
        return jsonify(response_data), 207  # Multi-status (partial success)
    else:
        return jsonify(response_data), 200
    

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

        # 4. Return file details
        files = [
                    {
                        "name": file.original_file_name,
                        "stored_name": file.stored_file_name,
                        "fileId": file.id,
                        "pages": file.total_pages,
                        "fileType": file.file_type
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