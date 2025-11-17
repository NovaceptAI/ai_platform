"""
Collaboration Models for Collaborate Stage Learning Path.

Database models for collaborative learning features including sessions, 
participants, documents, and real-time collaboration data.
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.db import db


class CollaborationSessionType(enum.Enum):
    """Types of collaboration sessions."""
    DISCUSSION = "discussion"
    PEER_REVIEW = "peer_review" 
    DOCUMENT_EDITING = "document_editing"
    PROJECT_MANAGEMENT = "project_management"
    STUDY_GROUP = "study_group"


class SessionStatus(enum.Enum):
    """Status of collaboration sessions."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ParticipantRole(enum.Enum):
    """Roles for session participants."""
    OWNER = "owner"
    MODERATOR = "moderator"
    EDITOR = "editor"
    COMMENTER = "commenter"
    VIEWER = "viewer"


class ReviewStatus(enum.Enum):
    """Status of peer reviews."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class CollaborationSession(db.Model):
    """Main collaboration session model."""
    
    __tablename__ = 'collaboration_sessions'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    session_type = Column(Enum(CollaborationSessionType), nullable=False)
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE)
    
    # Ownership
    owner_id = Column(String, nullable=False)  # References user
    
    # Settings and configuration
    settings = Column(JSON, default={})
    max_participants = Column(Integer, default=50)
    is_public = Column(Boolean, default=False)
    requires_approval = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    scheduled_start = Column(DateTime)
    scheduled_end = Column(DateTime)
    
    # Learning path context
    learning_path_id = Column(String)
    stage = Column(String, default='collaborate')
    
    # Relationships
    participants = relationship("SessionParticipant", back_populates="session", cascade="all, delete-orphan")
    documents = relationship("CollaborativeDocument", back_populates="session", cascade="all, delete-orphan")
    comments = relationship("CollaborationComment", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CollaborationSession {self.title} ({self.session_type.value})>"


class SessionParticipant(db.Model):
    """Participants in collaboration sessions."""
    
    __tablename__ = 'session_participants'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey('collaboration_sessions.id'), nullable=False)
    user_id = Column(String, nullable=False)
    role = Column(Enum(ParticipantRole), default=ParticipantRole.VIEWER)
    
    # Participation metadata
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_online = Column(Boolean, default=False)
    permissions = Column(JSON, default={})
    
    # Invitation and approval
    invited_by = Column(String)
    invitation_sent_at = Column(DateTime)
    approved_at = Column(DateTime)
    
    # Relationships
    session = relationship("CollaborationSession", back_populates="participants")
    
    def __repr__(self):
        return f"<Participant {self.user_id} in {self.session_id} as {self.role.value}>"


class CollaborativeDocument(db.Model):
    """Collaborative documents within sessions."""
    
    __tablename__ = 'collaborative_documents'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey('collaboration_sessions.id'), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, default='')
    
    # Versioning and collaboration
    version = Column(Integer, default=1)
    last_modified_by = Column(String)
    last_modified_at = Column(DateTime, default=datetime.utcnow)
    
    # Document metadata
    document_type = Column(String, default='text')  # text, markdown, rich_text
    settings = Column(JSON, default={})
    is_locked = Column(Boolean, default=False)
    locked_by = Column(String)
    
    # Created timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("CollaborationSession", back_populates="documents")
    operations = relationship("DocumentOperation", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CollaborativeDocument {self.title} v{self.version}>"


class DocumentOperation(db.Model):
    """Operations for operational transforms in collaborative editing."""
    
    __tablename__ = 'document_operations'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey('collaborative_documents.id'), nullable=False)
    user_id = Column(String, nullable=False)
    
    # Operation details
    operation_type = Column(String, nullable=False)  # insert, delete, retain
    position = Column(Integer, nullable=False)
    content = Column(Text)
    length = Column(Integer)
    
    # Operational transform metadata
    timestamp = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, nullable=False)
    client_id = Column(String)
    
    # Relationships
    document = relationship("CollaborativeDocument", back_populates="operations")
    
    def __repr__(self):
        return f"<Operation {self.operation_type} at {self.position} by {self.user_id}>"


class CollaborationComment(db.Model):
    """Comments and discussions within collaboration sessions."""
    
    __tablename__ = 'collaboration_comments'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey('collaboration_sessions.id'), nullable=False)
    user_id = Column(String, nullable=False)
    
    # Comment content
    content = Column(Text, nullable=False)
    content_type = Column(String, default='text')  # text, markdown, rich_text
    
    # Threading
    parent_id = Column(String, ForeignKey('collaboration_comments.id'))
    thread_id = Column(String)  # Root comment ID for threading
    
    # Position context (for document comments)
    document_id = Column(String, ForeignKey('collaborative_documents.id'))
    position_start = Column(Integer)
    position_end = Column(Integer)
    
    # Status and metadata
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(String)
    resolved_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Reactions and votes
    reactions = Column(JSON, default={})
    votes = Column(JSON, default={'up': 0, 'down': 0})
    
    # Relationships
    session = relationship("CollaborationSession", back_populates="comments")
    document = relationship("CollaborativeDocument")
    replies = relationship("CollaborationComment", remote_side=[id])
    
    def __repr__(self):
        return f"<Comment by {self.user_id} in {self.session_id}>"


class PeerReview(db.Model):
    """Peer review assignments and submissions."""
    
    __tablename__ = 'peer_reviews'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey('collaboration_sessions.id'), nullable=False)
    
    # Review participants
    reviewer_id = Column(String, nullable=False)
    reviewee_id = Column(String, nullable=False)
    
    # Assignment details
    assignment_title = Column(String(255), nullable=False)
    assignment_description = Column(Text)
    rubric = Column(JSON)  # Structured rubric data
    
    # Review content
    review_content = Column(Text)
    scores = Column(JSON)  # Rubric-based scores
    overall_score = Column(Integer)
    feedback_type = Column(String, default='structured')
    
    # Status and timing
    status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime)
    submitted_at = Column(DateTime)
    
    # Anonymity and settings
    is_anonymous = Column(Boolean, default=True)
    allow_revisions = Column(Boolean, default=True)
    
    # Original work being reviewed
    original_file_id = Column(String)  # Reference to uploaded file
    original_content = Column(Text)
    
    def __repr__(self):
        return f"<PeerReview {self.assignment_title} by {self.reviewer_id}>"


class ProjectTask(db.Model):
    """Tasks within collaborative projects."""
    
    __tablename__ = 'project_tasks'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey('collaboration_sessions.id'), nullable=False)
    
    # Task details
    title = Column(String(255), nullable=False)
    description = Column(Text)
    priority = Column(String, default='medium')  # low, medium, high, urgent
    status = Column(String, default='todo')  # todo, in_progress, review, done
    
    # Assignment
    assigned_to = Column(String)  # User ID
    created_by = Column(String, nullable=False)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Dependencies and organization
    depends_on = Column(JSON, default=[])  # List of task IDs
    tags = Column(JSON, default=[])
    category = Column(String)
    
    # Progress tracking
    progress_percentage = Column(Integer, default=0)
    estimated_hours = Column(Integer)
    actual_hours = Column(Integer)
    
    def __repr__(self):
        return f"<ProjectTask {self.title} ({self.status})>"


class CollaborationNotification(db.Model):
    """Notifications for collaboration events."""
    
    __tablename__ = 'collaboration_notifications'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    session_id = Column(String, ForeignKey('collaboration_sessions.id'))
    
    # Notification content
    title = Column(String(255), nullable=False)
    message = Column(Text)
    notification_type = Column(String, nullable=False)  # mention, assignment, deadline, etc.
    
    # Status
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    
    # Metadata
    notification_metadata = Column(JSON, default={})
    priority = Column(String, default='normal')
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime)
    
    def __repr__(self):
        return f"<Notification {self.notification_type} for {self.user_id}>"
