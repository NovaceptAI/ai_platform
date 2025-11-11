"""
Historical Timelines Model

Stores AI-generated historical timelines with events, dates, and relationships.
"""

from app.db import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer
from datetime import datetime
import uuid


class HistoricalTimeline(db.Model):
    __tablename__ = "historical_timelines"

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)

    # Timeline metadata
    title = Column(Text, nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)  # history, science, personal, project, etc.
    time_period = Column(String(100))  # "Ancient Rome", "WWII", "2020-2023", etc.

    # Input source
    input_type = Column(String(50), nullable=False)  # text, document, data
    input_text = Column(Text)  # Original user input
    document_url = Column(Text)  # Azure blob URL if uploaded document

    # Timeline data
    events = Column(JSONB, nullable=False, default=list)  # List of event objects
    """
    Event structure:
    {
        "id": "uuid",
        "title": "Event Title",
        "date": "1945-05-08",  # ISO format or partial (1945, 1945-05)
        "date_precision": "exact|year|month|decade|century|approximate",
        "description": "Event description",
        "significance": "Why this event matters",
        "category": "military|political|cultural|scientific|economic",
        "location": "Berlin, Germany",
        "people_involved": ["Person 1", "Person 2"],
        "related_event_ids": ["uuid1", "uuid2"],  # Causally connected events
        "sources": ["Source 1", "Source 2"],
        "image_url": "optional image URL"
    }
    """

    # Timeline analysis
    total_events = Column(Integer, default=0)
    date_range_start = Column(String(50))  # Earliest date
    date_range_end = Column(String(50))  # Latest date
    key_themes = Column(JSONB, default=list)  # ["war", "revolution", "innovation"]
    key_figures = Column(JSONB, default=list)  # ["Churchill", "Roosevelt", "Hitler"]

    # Visualization settings
    visualization_type = Column(String(50), default="linear")  # linear, branching, circular
    color_scheme = Column(String(50), default="default")
    display_options = Column(JSONB, default=dict)  # User preferences for display

    # AI generation metadata
    ai_model_used = Column(String(100))  # gpt-4, gpt-4-turbo, etc.
    generation_prompt = Column(Text)  # Prompt used for generation
    processing_time = Column(Integer)  # Processing time in seconds
    confidence_score = Column(Integer, default=0)  # 1-10 rating of extraction quality

    # Collaboration and sharing
    is_public = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    tags = Column(JSONB, default=list)  # User-defined tags

    # Azure storage
    azure_folder_path = Column(Text)  # Folder path in Azure blob storage

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert timeline to dictionary."""
        return {
            'id': str(self.id),
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'time_period': self.time_period,
            'input_type': self.input_type,
            'events': self.events,
            'total_events': self.total_events,
            'date_range_start': self.date_range_start,
            'date_range_end': self.date_range_end,
            'key_themes': self.key_themes,
            'key_figures': self.key_figures,
            'visualization_type': self.visualization_type,
            'color_scheme': self.color_scheme,
            'display_options': self.display_options,
            'confidence_score': self.confidence_score,
            'is_public': self.is_public,
            'is_favorite': self.is_favorite,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def get_user_timelines(user_id: str, limit: int = 50):
        """Get all timelines for a user."""
        return HistoricalTimeline.query.filter_by(user_id=user_id)\
            .order_by(HistoricalTimeline.created_at.desc())\
            .limit(limit)\
            .all()

    @staticmethod
    def get_user_timelines_count(user_id: str) -> int:
        """Get count of timelines for a user."""
        return HistoricalTimeline.query.filter_by(user_id=user_id).count()

    @staticmethod
    def get_timeline_by_id(timeline_id: str, user_id: str):
        """Get specific timeline by ID for a user."""
        return HistoricalTimeline.query.filter_by(
            id=timeline_id,
            user_id=user_id
        ).first()
