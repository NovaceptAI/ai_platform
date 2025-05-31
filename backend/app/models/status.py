# models/files.py

import uuid
from datetime import datetime
from db import db  # This is your instance of SQLAlchemy from db.py
from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.orm import relationship
from sqlalchemy import Text, Integer, DateTime

class ProcessingStatus(db.Model):
    __tablename__ = "processing_status"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey("uploaded_files.id"), nullable=False)
    total_pages = db.Column(Integer, nullable=False)
    pages_processed = db.Column(Integer, default=0)
    last_updated = db.Column(DateTime, default=datetime.utcnow)
    status_message = db.Column(Text, default="Starting...")