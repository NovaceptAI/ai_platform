"""
Learning Drawings Model

Stores student drawings with AI analysis and educational feedback.
"""

from app.db import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float
from datetime import datetime
import uuid


class LearningDrawing(db.Model):
    __tablename__ = "learning_drawings"

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)

    # Drawing metadata
    title = Column(Text, nullable=False, default="My Drawing")
    topic = Column(String(100), nullable=False, index=True)  # water_cycle, plant_structure, etc.
    age_group = Column(String(20), nullable=False)  # 5-7, 8-10, 11-13, 14+

    # Drawing storage
    drawing_image_url = Column(Text, nullable=False)  # Azure Blob URL with SAS
    canvas_width = Column(Integer, default=800)
    canvas_height = Column(Integer, default=600)

    # AI Analysis results
    detected_objects = Column(JSONB, nullable=False, default=list)  # ["sun", "cloud", "rain", "water"]
    recognized_concepts = Column(JSONB, default=list)  # ["evaporation", "precipitation", "condensation"]
    topic_match = Column(String(100))  # Detected topic from drawing
    confidence_score = Column(Float, default=0.0)  # 0.0 to 1.0

    # Educational feedback
    feedback_text = Column(Text)  # Main educational response
    accuracy_score = Column(Integer, default=0)  # 1-10 rating
    suggestions = Column(JSONB, default=list)  # ["Add arrows to show water movement", "Label the sun"]
    fun_fact = Column(Text)  # Interesting related fact

    # Azure Computer Vision raw data
    azure_cv_tags = Column(JSONB, default=list)  # Raw tags from Azure CV
    azure_cv_description = Column(Text)  # Azure CV description
    azure_cv_confidence = Column(Float, default=0.0)

    # Progress tracking
    is_favorite = Column(Boolean, default=False)
    badges_earned = Column(JSONB, default=list)  # ["Water Cycle Expert", "First Drawing"]
    completion_status = Column(String(20), default="analyzed")  # draft, analyzing, analyzed

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<LearningDrawing {self.id} - {self.title} ({self.topic})>"

    def to_dict(self):
        """Convert model to dictionary for JSON responses."""
        return {
            'id': str(self.id),
            'user_id': self.user_id,
            'title': self.title,
            'topic': self.topic,
            'age_group': self.age_group,
            'drawing_image_url': self.drawing_image_url,
            'canvas_width': self.canvas_width,
            'canvas_height': self.canvas_height,
            'detected_objects': self.detected_objects or [],
            'recognized_concepts': self.recognized_concepts or [],
            'topic_match': self.topic_match,
            'confidence_score': self.confidence_score,
            'feedback_text': self.feedback_text,
            'accuracy_score': self.accuracy_score,
            'suggestions': self.suggestions or [],
            'fun_fact': self.fun_fact,
            'azure_cv_tags': self.azure_cv_tags or [],
            'azure_cv_description': self.azure_cv_description,
            'azure_cv_confidence': self.azure_cv_confidence,
            'is_favorite': self.is_favorite,
            'badges_earned': self.badges_earned or [],
            'completion_status': self.completion_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def get_user_drawings(user_id: str, topic: str = None, limit: int = 50, offset: int = 0):
        """Get user's drawings with optional topic filter."""
        query = LearningDrawing.query.filter_by(user_id=user_id)

        if topic:
            query = query.filter_by(topic=topic)

        return query.order_by(LearningDrawing.created_at.desc()).limit(limit).offset(offset).all()

    @staticmethod
    def get_user_drawings_count(user_id: str, topic: str = None):
        """Get count of user's drawings."""
        query = LearningDrawing.query.filter_by(user_id=user_id)

        if topic:
            query = query.filter_by(topic=topic)

        return query.count()

    @staticmethod
    def get_user_topics_summary(user_id: str):
        """Get summary of topics user has worked on."""
        from sqlalchemy import func

        results = db.session.query(
            LearningDrawing.topic,
            func.count(LearningDrawing.id).label('count'),
            func.avg(LearningDrawing.accuracy_score).label('avg_score')
        ).filter_by(user_id=user_id).group_by(LearningDrawing.topic).all()

        return [
            {
                'topic': r.topic,
                'drawing_count': r.count,
                'average_score': round(r.avg_score, 1) if r.avg_score else 0
            }
            for r in results
        ]
