import uuid
from datetime import datetime
from app.models.files import UploadedFile
from app.db import db

def save_uploaded_file_metadata(user_id, original_file_name, blob_path, file_type, file_hash):
    stored_file_name = blob_path.split('/')[-1]

    new_file = UploadedFile(
        user_id=user_id,
        original_file_name=original_file_name,
        stored_file_name=stored_file_name,
        file_path=blob_path,
        file_type=file_type,
        hash=file_hash
    )
    db.session.add(new_file)
    db.session.commit()
    return new_file