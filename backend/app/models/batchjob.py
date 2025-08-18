# app/models/BatchJob.py
import uuid
from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db import db

class BatchJob(db.Model):
    __tablename__ = "batch_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Text, nullable=False)
    tool = Column(String(50), nullable=False)              # e.g., 'summarizer'
    status = Column(String(50), default="in_progress")     # in_progress, completed, failed
    percentage = Column(Integer, default=0)
    files_json = Column(JSONB, nullable=False)             # [{file_id, original_name, progress_id, status, percentage}, ...]

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "tool": self.tool,
            "status": self.status,
            "percentage": self.percentage,
            "files_json": self.files_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }