"""
Digital Debate Platform Models

Database models for AI-assisted real-time debates.
Supports text-based debates with AI analysis, voice/video via Agora SDK.
"""

from app.db import db
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum


class DebateStatus(enum.Enum):
    """Debate lifecycle status."""
    CREATED = "created"  # Debate created, waiting for participants
    WAITING = "waiting"  # Waiting for participants to join
    READY = "ready"  # All participants joined, ready to start
    IN_PROGRESS = "in_progress"  # Debate is active
    PAUSED = "paused"  # Temporarily paused
    COMPLETED = "completed"  # Debate finished
    CANCELLED = "cancelled"  # Debate cancelled


class DebateFormat(enum.Enum):
    """Debate format types."""
    PARLIAMENTARY = "parliamentary"  # Opening, Rebuttal, Closing
    LINCOLN_DOUGLAS = "lincoln_douglas"  # 1v1 value debate
    PUBLIC_FORUM = "public_forum"  # Team-based, accessible
    FREE_FORM = "free_form"  # Unstructured discussion


class ParticipantRole(enum.Enum):
    """Participant roles in debate."""
    PROPOSITION = "proposition"  # For the motion
    OPPOSITION = "opposition"  # Against the motion
    MODERATOR = "moderator"  # Debate moderator
    AUDIENCE = "audience"  # Observer/voter


class MessageType(enum.Enum):
    """Message types in debate."""
    OPENING = "opening"  # Opening statement
    ARGUMENT = "argument"  # Main argument
    REBUTTAL = "rebuttal"  # Counter-argument
    CLOSING = "closing"  # Closing statement
    CHAT = "chat"  # General chat/question
    SYSTEM = "system"  # System notification


class Debate(db.Model):
    """Core debate model."""

    __tablename__ = "debates"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(String, nullable=False, index=True)

    # Debate content
    motion = Column(Text, nullable=False)  # Debate motion/topic
    description = Column(Text)  # Additional context
    category = Column(String(100), index=True)  # politics, science, philosophy, etc.
    tags = Column(JSONB, default=list)  # ["climate", "policy", "economics"]

    # Format and structure
    format = Column(String(50), nullable=False, default="parliamentary")
    max_participants = Column(Integer, default=4)  # 2 per side
    time_limit_per_speech = Column(Integer, default=300)  # 5 minutes in seconds
    total_rounds = Column(Integer, default=3)  # Opening, Rebuttal, Closing
    current_round = Column(Integer, default=0)

    # Settings
    settings = Column(JSONB, default=dict)
    """
    Settings structure:
    {
        "allow_audience": true,
        "enable_voice": false,
        "enable_video": false,
        "auto_fact_check": true,
        "ai_moderation": true,
        "argument_analysis": true,
        "enable_voting": true,
        "public_debate": false,
        "require_approval": false,
        "agora_enabled": false,
        "agora_channel_name": null
    }
    """

    # Status and timing
    status = Column(String(20), nullable=False, default="created", index=True)
    scheduled_start = Column(DateTime, nullable=True)  # Optional scheduled time
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)

    # Results and analytics
    results = Column(JSONB, default=dict)
    """
    Results structure:
    {
        "winner": "proposition|opposition|tie",
        "vote_counts": {"proposition": 45, "opposition": 32},
        "ai_verdict": {"winner": "proposition", "reasoning": "..."},
        "key_moments": [{"timestamp": "...", "description": "..."}],
        "statistics": {
            "total_arguments": 12,
            "total_rebuttals": 8,
            "average_argument_strength": 7.5
        }
    }
    """

    # AI analysis summary
    ai_summary = Column(JSONB, default=dict)
    """
    AI summary structure:
    {
        "overall_quality": 8,
        "strongest_arguments": [{"participant": "...", "argument": "..."}],
        "logical_fallacies_detected": [...],
        "fact_check_summary": {...},
        "improvement_suggestions": [...]
    }
    """

    # WebSocket/Agora connection info
    session_id = Column(String(100), unique=True, index=True)  # For WebSocket rooms
    agora_channel_name = Column(String(100), nullable=True)  # Agora channel
    agora_app_id = Column(String(100), nullable=True)  # Agora app ID

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    participants = relationship("DebateParticipant", back_populates="debate", cascade="all, delete-orphan")
    messages = relationship("DebateMessage", back_populates="debate", cascade="all, delete-orphan")
    analytics = relationship("DebateAnalytics", back_populates="debate", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Debate {self.id}: {self.motion[:50]}>"

    @classmethod
    def get_user_debates(cls, user_id, status=None, limit=50, offset=0):
        """
        Get debates where user is creator or participant.

        Args:
            user_id: User ID
            status: Filter by status (optional)
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of Debate objects
        """
        # Get debates where user is creator
        query = cls.query.filter(
            db.or_(
                cls.creator_id == user_id,
                cls.participants.any(DebateParticipant.user_id == user_id)
            )
        )

        if status:
            query = query.filter_by(status=status)

        return query.order_by(cls.created_at.desc()).limit(limit).offset(offset).all()

    @classmethod
    def get_public_debates(cls, category=None, limit=20, offset=0):
        """Get public debates for discovery."""
        query = cls.query.filter(
            cls.settings['public_debate'].astext.cast(db.Boolean) == True,
            cls.status.in_(['created', 'waiting', 'ready', 'in_progress'])
        )

        if category:
            query = query.filter_by(category=category)

        return query.order_by(cls.created_at.desc()).limit(limit).offset(offset).all()

    def to_dict(self, include_participants=True, include_messages=False):
        """Convert to dictionary for API responses."""
        data = {
            'id': str(self.id),
            'creator_id': self.creator_id,
            'motion': self.motion,
            'description': self.description,
            'category': self.category,
            'tags': self.tags,
            'format': self.format,
            'max_participants': self.max_participants,
            'time_limit_per_speech': self.time_limit_per_speech,
            'total_rounds': self.total_rounds,
            'current_round': self.current_round,
            'settings': self.settings,
            'status': self.status,
            'scheduled_start': self.scheduled_start.isoformat() if self.scheduled_start else None,
            'actual_start': self.actual_start.isoformat() if self.actual_start else None,
            'actual_end': self.actual_end.isoformat() if self.actual_end else None,
            'results': self.results,
            'ai_summary': self.ai_summary,
            'session_id': self.session_id,
            'agora_channel_name': self.agora_channel_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_participants:
            data['participants'] = [p.to_dict() for p in self.participants]

        if include_messages:
            data['messages'] = [m.to_dict() for m in self.messages]

        return data


class DebateParticipant(db.Model):
    """Participants in a debate."""

    __tablename__ = "debate_participants"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    debate_id = Column(UUID(as_uuid=True), ForeignKey('debates.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)

    # Role and team
    role = Column(String(20), nullable=False)  # proposition, opposition, moderator, audience
    team = Column(String(20), nullable=True)  # A, B (for team debates)
    is_active = Column(Boolean, default=True)  # Currently in debate

    # Participation metadata
    display_name = Column(String(100), nullable=False)
    avatar_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)

    # Speaking stats
    total_speaking_time = Column(Integer, default=0)  # Seconds
    messages_count = Column(Integer, default=0)
    arguments_count = Column(Integer, default=0)
    rebuttals_count = Column(Integer, default=0)

    # Performance scores
    performance_score = Column(JSONB, default=dict)
    """
    Performance score structure:
    {
        "argument_strength": 7.5,
        "logical_consistency": 8.0,
        "evidence_quality": 6.5,
        "rebuttal_effectiveness": 7.0,
        "persuasiveness": 8.5,
        "overall_score": 7.5
    }
    """

    # Connection status (for real-time)
    is_connected = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=datetime.utcnow)

    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime, nullable=True)

    # Relationships
    debate = relationship("Debate", back_populates="participants")
    messages = relationship("DebateMessage", back_populates="participant", cascade="all, delete-orphan")
    analytics = relationship("DebateAnalytics", back_populates="participant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DebateParticipant {self.user_id} - {self.role} in {self.debate_id}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': str(self.id),
            'debate_id': str(self.debate_id),
            'user_id': self.user_id,
            'role': self.role,
            'team': self.team,
            'is_active': self.is_active,
            'display_name': self.display_name,
            'avatar_url': self.avatar_url,
            'bio': self.bio,
            'total_speaking_time': self.total_speaking_time,
            'messages_count': self.messages_count,
            'arguments_count': self.arguments_count,
            'rebuttals_count': self.rebuttals_count,
            'performance_score': self.performance_score,
            'is_connected': self.is_connected,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'left_at': self.left_at.isoformat() if self.left_at else None,
        }


class DebateMessage(db.Model):
    """Messages and arguments in a debate."""

    __tablename__ = "debate_messages"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    debate_id = Column(UUID(as_uuid=True), ForeignKey('debates.id', ondelete='CASCADE'), nullable=False, index=True)
    participant_id = Column(UUID(as_uuid=True), ForeignKey('debate_participants.id', ondelete='CASCADE'), nullable=False, index=True)

    # Message content
    message_type = Column(String(20), nullable=False, index=True)  # opening, argument, rebuttal, closing, chat, system
    content = Column(Text, nullable=False)
    round_number = Column(Integer, default=0)  # Which round this belongs to

    # Speaking metadata
    duration_seconds = Column(Integer, default=0)  # For voice messages
    audio_url = Column(Text, nullable=True)  # Azure blob URL for voice recording
    video_url = Column(Text, nullable=True)  # Azure blob URL for video recording

    # References
    reply_to_message_id = Column(UUID(as_uuid=True), ForeignKey('debate_messages.id', ondelete='SET NULL'), nullable=True)
    references = Column(JSONB, default=list)  # List of message IDs this responds to

    # Evidence and sources
    sources = Column(JSONB, default=list)  # [{"title": "...", "url": "...", "quote": "..."}]
    attachments = Column(JSONB, default=list)  # [{"type": "image", "url": "..."}]

    # AI analysis
    ai_analysis = Column(JSONB, default=dict)
    """
    AI analysis structure:
    {
        "argument_strength": 7.5,
        "logical_structure": {
            "claim": "...",
            "evidence": [...],
            "reasoning": "...",
            "conclusion": "..."
        },
        "fallacies_detected": [
            {"type": "ad_hominem", "severity": "minor", "explanation": "..."}
        ],
        "fact_checks": [
            {"claim": "...", "verdict": "true|false|unverifiable", "sources": [...]}
        ],
        "sentiment": "positive|negative|neutral",
        "persuasiveness": 8.0,
        "improvement_suggestions": [...]
    }
    """

    # Engagement metrics
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    reactions = Column(JSONB, default=dict)  # {"applause": 5, "disagree": 2}

    # Status
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime, nullable=True)
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    debate = relationship("Debate", back_populates="messages")
    participant = relationship("DebateParticipant", back_populates="messages")

    def __repr__(self):
        return f"<DebateMessage {self.id}: {self.message_type} in {self.debate_id}>"

    @classmethod
    def get_debate_messages(cls, debate_id, message_type=None, round_number=None, limit=100):
        """Get messages for a debate with optional filters."""
        query = cls.query.filter_by(debate_id=debate_id)

        if message_type:
            query = query.filter_by(message_type=message_type)

        if round_number is not None:
            query = query.filter_by(round_number=round_number)

        return query.order_by(cls.created_at.asc()).limit(limit).all()

    def to_dict(self, include_analysis=True):
        """Convert to dictionary for API responses."""
        data = {
            'id': str(self.id),
            'debate_id': str(self.debate_id),
            'participant_id': str(self.participant_id),
            'message_type': self.message_type,
            'content': self.content,
            'round_number': self.round_number,
            'duration_seconds': self.duration_seconds,
            'audio_url': self.audio_url,
            'video_url': self.video_url,
            'reply_to_message_id': str(self.reply_to_message_id) if self.reply_to_message_id else None,
            'references': self.references,
            'sources': self.sources,
            'attachments': self.attachments,
            'upvotes': self.upvotes,
            'downvotes': self.downvotes,
            'reactions': self.reactions,
            'is_edited': self.is_edited,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'is_flagged': self.is_flagged,
            'flag_reason': self.flag_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if include_analysis:
            data['ai_analysis'] = self.ai_analysis

        return data


class DebateAnalytics(db.Model):
    """Performance analytics for debate participants."""

    __tablename__ = "debate_analytics"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    debate_id = Column(UUID(as_uuid=True), ForeignKey('debates.id', ondelete='CASCADE'), nullable=False, index=True)
    participant_id = Column(UUID(as_uuid=True), ForeignKey('debate_participants.id', ondelete='CASCADE'), nullable=False, index=True)

    # Comprehensive performance metrics
    metrics = Column(JSONB, nullable=False, default=dict)
    """
    Metrics structure:
    {
        "argument_metrics": {
            "total_arguments": 5,
            "average_strength": 7.5,
            "strongest_argument_id": "uuid",
            "evidence_usage": 12,
            "logical_consistency": 8.0
        },
        "rebuttal_metrics": {
            "total_rebuttals": 3,
            "effectiveness_score": 7.0,
            "response_time_avg": 45  # seconds
        },
        "communication_metrics": {
            "clarity_score": 8.5,
            "conciseness_score": 7.0,
            "persuasiveness_score": 8.0,
            "emotional_appeal": 6.5
        },
        "fact_check_record": {
            "accurate_claims": 15,
            "inaccurate_claims": 2,
            "unverifiable_claims": 3,
            "accuracy_rate": 0.75
        },
        "engagement_metrics": {
            "total_upvotes_received": 45,
            "total_downvotes_received": 8,
            "average_reaction_count": 5.2
        }
    }
    """

    # Skills breakdown
    skills_assessment = Column(JSONB, default=dict)
    """
    Skills assessment structure:
    {
        "critical_thinking": 8,
        "logical_reasoning": 7.5,
        "evidence_evaluation": 7,
        "argumentation": 8.5,
        "active_listening": 7,
        "persuasion": 8,
        "respectful_discourse": 9
    }
    """

    # Improvement areas
    improvement_areas = Column(JSONB, default=list)
    """
    [
        {
            "area": "Evidence Quality",
            "current_score": 6.5,
            "suggestions": ["Cite more academic sources", "..."]
        }
    ]
    """

    # Comparison data
    peer_comparison = Column(JSONB, default=dict)
    """
    {
        "percentile_rank": 75,  # Better than 75% of debaters
        "category_rank": 12,  # Rank in this category
        "strengths_vs_peers": ["Logical reasoning", "Evidence usage"],
        "weaknesses_vs_peers": ["Response time"]
    }
    """

    # Historical performance (if available)
    historical_trend = Column(JSONB, default=dict)  # Performance over time

    # Timestamps
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    debate = relationship("Debate", back_populates="analytics")
    participant = relationship("DebateParticipant", back_populates="analytics")

    def __repr__(self):
        return f"<DebateAnalytics {self.id} for participant {self.participant_id}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': str(self.id),
            'debate_id': str(self.debate_id),
            'participant_id': str(self.participant_id),
            'metrics': self.metrics,
            'skills_assessment': self.skills_assessment,
            'improvement_areas': self.improvement_areas,
            'peer_comparison': self.peer_comparison,
            'historical_trend': self.historical_trend,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None,
        }
