# app/models/readability_results.py
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.ext.mutable import MutableDict
from app.db import db

class ReadabilityAnalysisResult(db.Model):
    """Store readability and style analysis results for documents."""
    __tablename__ = 'readability_analysis_results'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('uploaded_files.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Document-level metrics
    doc_metrics = db.Column(JSONB, nullable=True)

    # Per-page analysis
    per_page_analysis = db.Column(JSONB, nullable=True)

    # Style analysis
    style_analysis = db.Column(JSONB, nullable=True)

    # Readability scores
    readability_scores = db.Column(JSONB, nullable=True)

    # Issues and recommendations
    issues = db.Column(JSONB, nullable=True)
    recommendations = db.Column(JSONB, nullable=True)

    # Summary
    summary = db.Column(db.Text, nullable=True)
    target_audience = db.Column(db.String(100), nullable=True)

    # Metadata
    version = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    file = db.relationship('UploadedFile', lazy='joined')

    def __repr__(self):
        return f"<ReadabilityAnalysisResult(file_id={self.file_id}, target_audience={self.target_audience})>"
