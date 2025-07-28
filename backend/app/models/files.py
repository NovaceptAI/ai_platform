# models/files.py

import uuid
from datetime import datetime
from app.db import db  # This is your instance of SQLAlchemy from db.py
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, Text, Integer, DateTime, String


class UploadedFile(db.Model):
    __tablename__ = "uploaded_files"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_file_name = db.Column(Text, nullable=False)  # ✅ New
    stored_file_name = db.Column(Text, nullable=False)     # ✅ New
    file_path = db.Column(Text, nullable=False)
    file_type = db.Column(Text, nullable=False)
    total_pages = db.Column(Integer)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    status = db.Column(Text, default="pending")
    hash = db.Column(String(64), unique=True, nullable=True)

    pages = db.relationship("FilePage", backref="file", cascade="all, delete-orphan")
    progress = db.relationship("ProcessingStatus", backref="file", uselist=False, cascade="all, delete-orphan")


class FilePage(db.Model):
    __tablename__ = "file_pages"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey("uploaded_files.id"), nullable=False)
    page_number = db.Column(Integer, nullable=False)
    page_text = db.Column(Text, nullable=False)
    page_summary = db.Column(Text)
    created_at = db.Column(DateTime, default=datetime.utcnow)
