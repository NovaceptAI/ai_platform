"""
Kid Art Creation Model

Database model for storing AI-generated artwork created by children.
Supports multiple variations, collections, favorites, and stories.
"""

from app.db import db
from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid


class KidArtCreation(db.Model):
    """Model for kid-created AI art with educational and creative features."""

    __tablename__ = "kid_art_creations"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)

    # Art metadata
    title = Column(Text, nullable=False, default="My Artwork")
    prompt_text = Column(Text, nullable=False)  # What the kid described
    age_group = Column(String(10), nullable=False)  # "5-7", "8-10", "11-14"

    # Art configuration
    art_style = Column(String(50), nullable=False)  # cartoon, watercolor, etc.
    color_palette = Column(String(50), nullable=False)  # vibrant, pastel, rainbow
    num_variations = Column(Integer, nullable=False, default=1)  # 1-4

    # Azure storage paths
    azure_folder_path = Column(Text, nullable=False)
    images = Column(JSONB, nullable=False)  # Array of {variation_num, image_url, thumbnail_url}

    # Creative elements
    story_text = Column(Text, nullable=True)  # Kid's story about the artwork
    is_favorite = Column(Boolean, default=False, index=True)
    character_name = Column(String(100), nullable=True)  # For recurring characters
    collection_name = Column(String(100), nullable=True, index=True)  # Group related art

    # Safety & metadata
    original_prompt = Column(Text, nullable=False)  # Before sanitization
    sanitized_prompt = Column(Text, nullable=False)  # After safety filter
    generation_metadata = Column(JSONB, default=dict)  # DALL-E params, safety flags

    # Source tracking (optional - if from Knowledge Vault file)
    source_file_id = Column(UUID(as_uuid=True), ForeignKey('uploaded_files.id', ondelete='SET NULL'), nullable=True)
    source_file = relationship('UploadedFile', foreign_keys=[source_file_id])

    # Status
    status = Column(String(20), default='active', index=True)  # active, archived

    # Timestamps
    created_at = Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<KidArtCreation {self.id}: {self.title}>"

    @classmethod
    def get_user_artworks(cls, user_id, limit=20, offset=0, is_favorite=None, collection_name=None):
        """
        Get artworks for a user with optional filters.

        Args:
            user_id: User ID
            limit: Number of results
            offset: Pagination offset
            is_favorite: Filter by favorite status (optional)
            collection_name: Filter by collection (optional)

        Returns:
            List of KidArtCreation objects
        """
        query = cls.query.filter_by(user_id=user_id, status='active')

        if is_favorite is not None:
            query = query.filter_by(is_favorite=is_favorite)

        if collection_name:
            query = query.filter_by(collection_name=collection_name)

        return query.order_by(cls.created_at.desc()).limit(limit).offset(offset).all()

    @classmethod
    def get_user_artworks_count(cls, user_id, is_favorite=None, collection_name=None):
        """Get total count of artworks for a user."""
        query = cls.query.filter_by(user_id=user_id, status='active')

        if is_favorite is not None:
            query = query.filter_by(is_favorite=is_favorite)

        if collection_name:
            query = query.filter_by(collection_name=collection_name)

        return query.count()

    @classmethod
    def get_user_collections(cls, user_id):
        """Get list of unique collection names for a user."""
        collections = db.session.query(cls.collection_name).filter(
            cls.user_id == user_id,
            cls.status == 'active',
            cls.collection_name.isnot(None)
        ).distinct().all()

        return [c[0] for c in collections]

    def to_dict(self, include_images=True):
        """Convert to dictionary for API responses."""
        data = {
            'id': str(self.id),
            'user_id': self.user_id,
            'title': self.title,
            'prompt_text': self.prompt_text,
            'age_group': self.age_group,
            'art_style': self.art_style,
            'color_palette': self.color_palette,
            'num_variations': self.num_variations,
            'story_text': self.story_text,
            'is_favorite': self.is_favorite,
            'character_name': self.character_name,
            'collection_name': self.collection_name,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_images:
            data['images'] = self.images
            data['azure_folder_path'] = self.azure_folder_path

        return data
