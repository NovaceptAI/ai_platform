# app/models/data_stories.py
"""
Data Story Creations Model

Stores user-generated data analysis stories from the Data Story Builder tool.
Each story includes data profiling, AI insights, visualizations, and exports.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db import db


class DataStoryCreation(db.Model):
    """
    Stores data analysis stories with persistent Azure storage.

    Two-stage process:
    1) Upload + Profile + AI Insights
    2) Generate Visualizations + Export PDF/HTML
    """
    __tablename__ = "data_story_creations"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)  # Indexed for fast user queries

    # Story metadata
    title = Column(Text, nullable=False)  # Story title
    dataset_name = Column(Text, nullable=False)  # Original filename

    # Source tracking
    source_type = Column(String(20), nullable=False)  # 'upload', 'vault', 'url'
    source_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploaded_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    source_url = Column(Text, nullable=True)  # If loaded from URL

    # State management
    current_stage = Column(Integer, default=1)  # 1 or 2
    status = Column(String(20), default='active')  # 'active', 'orphaned'

    # Azure storage paths
    azure_folder_path = Column(Text, nullable=False)  # {user_id}/data_stories/{id}/
    thumbnail_url = Column(Text, nullable=True)  # Preview image
    pdf_url = Column(Text, nullable=True)  # Final PDF export (Stage 2)
    html_url = Column(Text, nullable=True)  # Interactive HTML export (Stage 2)

    # Data content (JSONB for flexibility)
    data_profile = Column(JSONB, nullable=False)  # Stage 1 output
    # Structure: {
    #   "dataset_info": {
    #     "total_rows": 1000,
    #     "total_columns": 8,
    #     "memory_usage": "64 KB",
    #     "file_name": "sales_data.csv"
    #   },
    #   "columns": [
    #     {
    #       "name": "date",
    #       "type": "datetime",
    #       "missing": 0,
    #       "missing_percent": 0,
    #       "unique": 365,
    #       "stats": {...}  // For numeric columns
    #     }
    #   ],
    #   "suggested_charts": [...]
    # }

    insights_data = Column(JSONB, nullable=True)  # Stage 1 output
    # Structure: {
    #   "key_insights": [
    #     {
    #       "id": "insight_1",
    #       "type": "trend|correlation|anomaly|pattern",
    #       "title": "Revenue Growing 15% YoY",
    #       "description": "Detailed description...",
    #       "confidence": "high|medium|low",
    #       "supporting_data": {...}
    #     }
    #   ],
    #   "narrative": {
    #     "introduction": "This dataset reveals...",
    #     "key_findings": "Three major patterns...",
    #     "conclusion": "Overall, the data..."
    #   },
    #   "recommendations": ["Focus on...", "Investigate..."]
    # }

    visualizations = Column(JSONB, nullable=True)  # Stage 2 output
    # Structure: [
    #   {
    #     "id": "viz_1",
    #     "insight_id": "insight_1",  // Links to insight
    #     "chart_type": "line|bar|scatter|histogram|pie|heatmap",
    #     "title": "Revenue Trend Over Time",
    #     "chart_url": "https://azure.../chart1.png",
    #     "chart_data": {...},  // Chart configuration
    #     "width": 800,
    #     "height": 600
    #   }
    # ]

    story_metadata = Column(JSONB, default=dict)  # Generation metadata
    # Structure: {
    #   "total_rows": 1000,
    #   "total_columns": 8,
    #   "selected_columns": ["date", "revenue"],
    #   "processing_time": "3m 45s",
    #   "ai_model_used": "gpt-4",
    #   "charts_generated": 5,
    #   "stage_1_completed_at": "...",
    #   "stage_2_completed_at": "..."
    # }

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    source_file = relationship(
        "UploadedFile",
        foreign_keys=[source_file_id],
        backref="data_story_creations"
    )

    def to_dict(self, include_full_data=False):
        """
        Convert model to dictionary for API responses.

        Args:
            include_full_data: If True, includes all JSONB data. If False, only metadata.

        Returns:
            Dictionary representation of the data story
        """
        result = {
            'id': str(self.id),
            'user_id': self.user_id,
            'title': self.title,
            'dataset_name': self.dataset_name,
            'source_type': self.source_type,
            'current_stage': self.current_stage,
            'status': self.status,
            'thumbnail_url': self.thumbnail_url,
            'pdf_url': self.pdf_url,
            'html_url': self.html_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

        # Include source file info if available
        if self.source_file_id:
            result['source_file_id'] = str(self.source_file_id)
            if self.source_file:
                result['source_file_name'] = self.source_file.original_file_name

        # Include source URL if available
        if self.source_url:
            result['source_url'] = self.source_url

        # Include metadata summary
        if self.story_metadata:
            result['metadata_summary'] = {
                'total_rows': self.story_metadata.get('total_rows'),
                'total_columns': self.story_metadata.get('total_columns'),
                'charts_generated': self.story_metadata.get('charts_generated', 0)
            }

        # Include full data if requested (for detail view)
        if include_full_data:
            result['data_profile'] = self.data_profile
            result['insights_data'] = self.insights_data
            result['visualizations'] = self.visualizations
            result['story_metadata'] = self.story_metadata

        return result

    def mark_as_orphaned(self):
        """
        Mark data story as orphaned when source file is deleted.
        Removes source_file_id reference but keeps the story.
        """
        self.status = 'orphaned'
        self.source_file_id = None
        self.updated_at = datetime.utcnow()

    @classmethod
    def get_user_stories(cls, user_id, limit=None, offset=0):
        """
        Get all data stories for a user, ordered by creation date (newest first).

        Args:
            user_id: User's ID
            limit: Maximum number of results (None for all)
            offset: Number of results to skip (for pagination)

        Returns:
            List of DataStoryCreation objects
        """
        query = cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc())

        if limit:
            query = query.limit(limit).offset(offset)

        return query.all()

    @classmethod
    def get_user_stories_count(cls, user_id):
        """Get total count of user's data stories for pagination."""
        return cls.query.filter_by(user_id=user_id).count()
