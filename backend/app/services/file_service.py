import uuid
from datetime import datetime
from models.files import UploadedFile
from db import db

def save_uploaded_file_metadata(filename, blob_path, content_type, file_hash):
    new_file = UploadedFile(
        id=uuid.uuid4(),
        file_name=filename,
        file_path=blob_path,
        file_type=content_type,
        hash=file_hash,  # new field
        total_pages=0,
        created_at=datetime.utcnow(),
        status="pending"
    )
    db.session.add(new_file)
    db.session.commit()
    return new_file