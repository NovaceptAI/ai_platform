# models/files.py

import uuid
from datetime import datetime
from app.db import db  # This is your instance of SQLAlchemy from db.py
from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.orm import relationship
from sqlalchemy import Text, Integer, DateTime, ForeignKey, String

class ProcessingStatus(db.Model):
    __tablename__ = "processing_status"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey("uploaded_files.id"), nullable=True)
    total_pages = db.Column(Integer, nullable=False)
    pages_processed = db.Column(Integer, default=0)
    last_updated = db.Column(DateTime, default=datetime.utcnow)
    status_message = db.Column(Text, default="Starting...")


class Progress(db.Model):
    __tablename__ = 'progress'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = db.Column(UUID(as_uuid=True), ForeignKey('uploaded_files.id'), nullable=True)
    status = db.Column(String(50), default='in_progress')
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.String, nullable=False)
    tool = db.Column(String(50), nullable=False)
    percentage = db.Column(Integer, default=0)
    
