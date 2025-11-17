"""
3D Model Creation Model

Database model for storing AI-generated 3D objects.
Supports multiple export formats, preview images, and interactive viewing.
"""

from app.db import db
from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid


class ThreeDModelCreation(db.Model):
    """Model for AI-generated 3D objects."""

    __tablename__ = "three_d_model_creations"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)

    # Model metadata
    title = Column(Text, nullable=False, default="My 3D Model")
    prompt_text = Column(Text, nullable=False)  # User's description
    category = Column(String(50), nullable=True, index=True)  # object, character, building, nature

    # Generation configuration
    complexity_level = Column(String(20), nullable=False)  # simple, medium, detailed
    style = Column(String(50), nullable=False)  # realistic, cartoon, low_poly, clay, wireframe

    # Azure storage paths
    azure_folder_path = Column(Text, nullable=False)
    model_files = Column(JSONB, nullable=False)  # {glb_url, obj_url, stl_url}

    # Preview images from different angles
    preview_images = Column(JSONB, nullable=False)  # [{angle: 'front', url: '...'}, ...]
    thumbnail_url = Column(Text, nullable=True)  # Main thumbnail (perspective view)

    # Model properties
    object_type = Column(String(100), nullable=True)  # extracted from prompt
    vertex_count = Column(Integer, nullable=True)
    polygon_count = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)

    # Rendering metadata
    camera_settings = Column(JSONB, default=dict)  # {position, rotation, zoom, target}
    lighting_config = Column(JSONB, default=dict)  # {ambient, directional, point_lights}
    material_properties = Column(JSONB, default=dict)  # {base_color, roughness, metalness}
    bounding_box = Column(JSONB, default=dict)  # {min: [x,y,z], max: [x,y,z], dimensions: [w,h,d]}

    # AI generation metadata
    generation_metadata = Column(JSONB, default=dict)  # {model_used, generation_time, parameters}

    # Source tracking (optional - if from Knowledge Vault file)
    source_file_id = Column(UUID(as_uuid=True), ForeignKey('uploaded_files.id', ondelete='SET NULL'), nullable=True)
    source_file = relationship('UploadedFile', foreign_keys=[source_file_id])

    # Status
    status = Column(String(20), default='active', index=True)  # active, archived

    # Timestamps
    created_at = Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ThreeDModelCreation {self.id}: {self.title}>"

    @classmethod
    def get_user_models(cls, user_id, limit=20, offset=0, category=None, style=None):
        """
        Get 3D models for a user with optional filters.

        Args:
            user_id: User ID
            limit: Number of results
            offset: Pagination offset
            category: Filter by category (optional)
            style: Filter by style (optional)

        Returns:
            List of ThreeDModelCreation objects
        """
        query = cls.query.filter_by(user_id=user_id, status='active')

        if category:
            query = query.filter_by(category=category)

        if style:
            query = query.filter_by(style=style)

        return query.order_by(cls.created_at.desc()).limit(limit).offset(offset).all()

    @classmethod
    def get_user_models_count(cls, user_id, category=None, style=None):
        """Get total count of models for a user."""
        query = cls.query.filter_by(user_id=user_id, status='active')

        if category:
            query = query.filter_by(category=category)

        if style:
            query = query.filter_by(style=style)

        return query.count()

    @classmethod
    def get_user_categories(cls, user_id):
        """Get list of unique categories for a user."""
        categories = db.session.query(cls.category).filter(
            cls.user_id == user_id,
            cls.status == 'active',
            cls.category.isnot(None)
        ).distinct().all()

        return [c[0] for c in categories]

    def to_dict(self, include_files=True):
        """Convert to dictionary for API responses."""
        data = {
            'id': str(self.id),
            'user_id': self.user_id,
            'title': self.title,
            'prompt_text': self.prompt_text,
            'category': self.category,
            'complexity_level': self.complexity_level,
            'style': self.style,
            'object_type': self.object_type,
            'vertex_count': self.vertex_count,
            'polygon_count': self.polygon_count,
            'file_size_bytes': self.file_size_bytes,
            'thumbnail_url': self.thumbnail_url,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_files:
            data['model_files'] = self.model_files
            data['preview_images'] = self.preview_images
            data['azure_folder_path'] = self.azure_folder_path
            data['camera_settings'] = self.camera_settings
            data['lighting_config'] = self.lighting_config
            data['material_properties'] = self.material_properties
            data['bounding_box'] = self.bounding_box

        return data
