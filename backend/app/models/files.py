# models/files.py

import uuid
from datetime import datetime
from app.db import db  # This is your instance of SQLAlchemy from db.py
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, Text, Integer, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB  # if Postgres; else use db.JSON


class UploadedFile(db.Model):
    __tablename__ = "uploaded_files"
    __table_args__ = (
        db.UniqueConstraint('user_id', 'hash', name='uq_user_file_hash'),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.String, nullable=False)  # ✅ NEW
    original_file_name = db.Column(Text, nullable=False)
    stored_file_name = db.Column(Text, nullable=False)
    file_path = db.Column(Text, nullable=False)
    file_type = db.Column(Text, nullable=False)
    total_pages = db.Column(Integer)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    status = db.Column(Text, default="pending")
    hash = db.Column(String(64), nullable=True)

    pages = db.relationship("FilePage", backref="file", cascade="all, delete-orphan")
    progress = db.relationship("ProcessingStatus", backref="file", uselist=False, cascade="all, delete-orphan")


class FilePage(db.Model):
    __tablename__ = "file_pages"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey("uploaded_files.id"), nullable=False)
    page_number = db.Column(Integer, nullable=False)
    page_text = db.Column(Text, nullable=False)
    page_summary = db.Column(Text)
    page_topics = db.Column(JSONB)  # or JSONB if Postgres
    page_prompts = db.Column(JSONB)  # Creative writing prompts generated from page text
    created_at = db.Column(DateTime, default=datetime.utcnow)


class FileTimestamp(db.Model):
    __tablename__ = "file_timestamps"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey("uploaded_files.id"), nullable=False)
    page_id = db.Column(UUID(as_uuid=True), db.ForeignKey("file_pages.id"), nullable=False)
    sequence_number = db.Column(Integer, nullable=False)  # Original SRT sequence
    start_time = db.Column(String(20), nullable=False)    # SRT format: HH:MM:SS,mmm
    end_time = db.Column(String(20), nullable=False)      # SRT format: HH:MM:SS,mmm
    start_seconds = db.Column(db.Float, nullable=False)   # Seconds for easier processing
    end_seconds = db.Column(db.Float, nullable=False)     # Seconds for easier processing
    duration = db.Column(db.Float, nullable=False)        # Duration in seconds
    original_text = db.Column(Text, nullable=False)       # Original segment text from SRT
    created_at = db.Column(DateTime, default=datetime.utcnow)

    # Relationships
    file = db.relationship("UploadedFile", backref="timestamps")
    page = db.relationship("FilePage", backref="timestamps")
