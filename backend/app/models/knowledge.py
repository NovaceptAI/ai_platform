import uuid
from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db import db


class WebScrapeJob(db.Model):
    __tablename__ = "web_scrape_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    domain = Column(String(255))
    title = Column(Text)
    status = Column(String(50), default="pending")  # pending, in_progress, done, failed
    progress = Column(Integer, default=0)
    task_id = Column(String(100))
    error = Column(Text)
    result_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_items.id"), nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "url": self.url,
            "domain": self.domain,
            "title": self.title,
            "status": self.status,
            "progress": self.progress,
            "task_id": self.task_id,
            "error": self.error,
            "result_id": str(self.result_id) if self.result_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class KnowledgeItem(db.Model):
    __tablename__ = "knowledge_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Text, nullable=False)
    source_type = Column(String(50), default="web")
    source_url = Column(Text)
    title = Column(Text)
    summary = Column(Text)
    structured_json = Column(JSONB)  # normalized/LLM-structured data
    metadata_json = Column(JSONB)    # any extra metadata
    blob_path_raw = Column(Text)     # raw html blob path
    blob_path_text = Column(Text)    # extracted text blob path
    saved = Column(db.Boolean, default=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "title": self.title,
            "summary": self.summary,
            "structured_json": self.structured_json,
            "metadata_json": self.metadata_json,
            "blob_path_raw": self.blob_path_raw,
            "blob_path_text": self.blob_path_text,
            "saved": self.saved,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

