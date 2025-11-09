# app/models/comics.py
"""
Comic Creations Model

Stores user-generated comic strip creations from the Story to Comics Creator tool.
Each comic is persisted with its panels stored in Azure Blob Storage.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db import db


class ComicCreation(db.Model):
    """
    Stores comic strip creations with persistent Azure storage.

    Supports multiple source types: file upload, knowledge vault, or text prompt.
    Handles orphaned state when source file is deleted.
    """
    __tablename__ = "comic_creations"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)  # Indexed for fast user queries

    # Comic metadata
    title = Column(Text, nullable=False)  # Generated comic title
    source_type = Column(String(20), nullable=False)  # 'file', 'vault', 'text'

    # Source tracking (nullable for text prompts and orphaned comics)
    source_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploaded_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    source_text_preview = Column(Text, nullable=True)  # First 200 chars if text source

    # State management
    status = Column(String(20), default='active')  # 'active', 'orphaned'

    # Comic configuration
    total_panels = Column(Integer, nullable=False)
    style = Column(String(20), nullable=False)  # 'vivid' or 'natural'

    # Azure storage paths
    azure_folder_path = Column(Text, nullable=False)  # {user_id}/comics/{comic_id}/
    thumbnail_url = Column(Text, nullable=True)  # URL to first panel (for gallery preview)

    # Comic content (JSONB for flexibility)
    panels_data = Column(JSONB, nullable=False)  # Array of panel objects with Azure URLs
    # Structure: [{
    #   "panel_number": 1,
    #   "title": "Panel Title",
    #   "scene_description": "...",
    #   "dialogue": ["Character: speech"],
    #   "narration": "...",
    #   "image_url": "https://azure.blob.../panel_1.png",
    #   "image_prompt": "...",
    #   "revised_prompt": "..."
    # }]

    comic_metadata = Column(JSONB, default=dict)  # Generation options, AI metadata, etc.
    # Structure: {
    #   "generation_options": {"num_panels": 6, "style": "vivid"},
    #   "ai_metadata": {...},
    #   "source_info": {...}
    # }

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    source_file = relationship(
        "UploadedFile",
        foreign_keys=[source_file_id],
        backref="comic_creations"
    )

    def to_dict(self, include_panels=False):
        """
        Convert model to dictionary for API responses.

        Args:
            include_panels: If True, includes full panels_data. If False, only metadata.

        Returns:
            Dictionary representation of the comic
        """
        result = {
            'id': str(self.id),
            'user_id': self.user_id,
            'title': self.title,
            'source_type': self.source_type,
            'status': self.status,
            'total_panels': self.total_panels,
            'style': self.style,
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

        # Include full panels data if requested (for detail view)
        if include_panels:
            result['panels'] = self.panels_data
            result['metadata'] = self.comic_metadata

        return result

    def mark_as_orphaned(self):
        """
        Mark comic as orphaned when source file is deleted.
        Removes source_file_id reference but keeps the comic.
        """
        self.status = 'orphaned'
        self.source_file_id = None
        self.updated_at = datetime.utcnow()

    @classmethod
    def get_user_comics(cls, user_id, limit=None, offset=0):
        """
        Get all comics for a user, ordered by creation date (newest first).

        Args:
            user_id: User's ID
            limit: Maximum number of results (None for all)
            offset: Number of results to skip (for pagination)

        Returns:
            List of ComicCreation objects
        """
        query = cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc())

        if limit:
            query = query.limit(limit).offset(offset)

        return query.all()

    @classmethod
    def get_user_comics_count(cls, user_id):
        """Get total count of user's comics for pagination."""
        return cls.query.filter_by(user_id=user_id).count()
