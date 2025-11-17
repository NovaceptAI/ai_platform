# app/models/presentations.py
"""
Presentation Creations Model

Stores user-generated PowerPoint presentations from the AI Presentation Builder tool.
Each presentation is persisted with slides stored in Azure Blob Storage.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db import db


class PresentationCreation(db.Model):
    """
    Stores PowerPoint presentation creations with persistent Azure storage.

    Supports multiple source types: file upload, knowledge vault, or topic/text prompt.
    Two-stage process: 1) Generate content, 2) Add images and create PPTX
    """
    __tablename__ = "presentation_creations"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)  # Indexed for fast user queries

    # Presentation metadata
    title = Column(Text, nullable=False)  # Presentation title
    source_type = Column(String(20), nullable=False)  # 'file', 'vault', 'text'

    # Source tracking (nullable for text prompts and orphaned presentations)
    source_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploaded_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    source_text_preview = Column(Text, nullable=True)  # First 200 chars if text source

    # State management
    status = Column(String(20), default='active')  # 'active', 'orphaned'

    # Presentation configuration
    total_slides = Column(Integer, nullable=False)
    theme = Column(String(50), nullable=False)  # Theme name
    image_style = Column(String(20), nullable=True)  # 'professional' or 'creative' (set in stage 2)

    # Azure storage paths
    azure_folder_path = Column(Text, nullable=False)  # {user_id}/presentations/{presentation_id}/
    pptx_url = Column(Text, nullable=True)  # URL to .pptx file with SAS token (created in stage 2)
    thumbnail_url = Column(Text, nullable=True)  # URL to first slide preview image

    # Presentation content (JSONB for flexibility)
    slides_data = Column(JSONB, nullable=False)  # Array of slide objects
    # Structure: [{
    #   "slide_number": 1,
    #   "slide_type": "title|content|chart|conclusion",
    #   "title": "Slide Title",
    #   "subtitle": "Subtitle (for title slides)",
    #   "content": ["Bullet 1", "Bullet 2"],
    #   "content_type": "bullets|paragraph|chart",
    #   "chart_type": "bar|line|pie",
    #   "chart_data": {...},
    #   "notes": "Speaker notes",
    #   "user_wants_image": true/false,
    #   "image_prompt": "DALL-E prompt",
    #   "image_url": "https://azure.../slide_X.png"
    # }]

    preview_images = Column(JSONB, nullable=True)  # Array of preview image URLs for browser viewing
    # Structure: ["url_to_slide1.png", "url_to_slide2.png", ...]

    presentation_metadata = Column(JSONB, default=dict)  # Generation options, AI metadata, etc.
    # Structure: {
    #   "generation_options": {"total_slides": 10, "theme": "professional_blue"},
    #   "source_info": {...},
    #   "ai_metadata": {...},
    #   "stage": 1 or 2  // Which stage the presentation is in
    # }

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    source_file = relationship(
        "UploadedFile",
        foreign_keys=[source_file_id],
        backref="presentation_creations"
    )

    def to_dict(self, include_slides=False):
        """
        Convert model to dictionary for API responses.

        Args:
            include_slides: If True, includes full slides_data. If False, only metadata.

        Returns:
            Dictionary representation of the presentation
        """
        result = {
            'id': str(self.id),
            'user_id': self.user_id,
            'title': self.title,
            'source_type': self.source_type,
            'status': self.status,
            'total_slides': self.total_slides,
            'theme': self.theme,
            'image_style': self.image_style,
            'pptx_url': self.pptx_url,
            'thumbnail_url': self.thumbnail_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        # Include source file info if available
        if self.source_file_id:
            result['source_file_id'] = str(self.source_file_id)
            if self.source_file:
                result['source_file_name'] = self.source_file.original_file_name

        # Include text preview if text source
        if self.source_type == 'text' and self.source_text_preview:
            result['source_text_preview'] = self.source_text_preview

        # Include metadata
        result['metadata'] = self.presentation_metadata

        # Include full slides data if requested (for detail view)
        if include_slides:
            result['slides'] = self.slides_data
            result['preview_images'] = self.preview_images

        return result

    def mark_as_orphaned(self):
        """
        Mark presentation as orphaned when source file is deleted.
        Removes source_file_id reference but keeps the presentation.
        """
        self.status = 'orphaned'
        self.source_file_id = None
        self.updated_at = datetime.utcnow()

    @classmethod
    def get_user_presentations(cls, user_id, limit=None, offset=0):
        """
        Get all presentations for a user, ordered by creation date (newest first).

        Args:
            user_id: User's ID
            limit: Maximum number of results (None for all)
            offset: Number of results to skip (for pagination)

        Returns:
            List of PresentationCreation objects
        """
        query = cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc())

        if limit:
            query = query.limit(limit).offset(offset)

        return query.all()

    @classmethod
    def get_user_presentations_count(cls, user_id):
        """Get total count of user's presentations for pagination."""
        return cls.query.filter_by(user_id=user_id).count()
