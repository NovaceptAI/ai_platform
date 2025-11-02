
import uuid
from datetime import datetime
from app.db import db
from sqlalchemy.dialects.postgresql import UUID

class LearningPath(db.Model):
    __tablename__ = 'learning_paths'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    est_minutes = db.Column(db.Integer, default=60)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    steps = db.relationship('LearningPathStep', back_populates='path', cascade='all, delete-orphan', order_by='LearningPathStep.position')

class LearningPathStep(db.Model):
    __tablename__ = 'learning_path_steps'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = db.Column(UUID(as_uuid=True), db.ForeignKey('learning_paths.id', ondelete='CASCADE'), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    tool_key = db.Column(db.String(100), nullable=False)
    config = db.Column(db.JSON, default=dict)
    title = db.Column(db.String(200))
    instructions = db.Column(db.Text)
    path = db.relationship('LearningPath', back_populates='steps')
    __table_args__ = (db.UniqueConstraint('path_id', 'position', name='uq_path_step_position'),)

class UserLearningPath(db.Model):
    __tablename__ = 'user_learning_paths'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    path_id = db.Column(UUID(as_uuid=True), db.ForeignKey('learning_paths.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(32), default='active')
    current_step = db.Column(db.Integer, default=1)
    progress_id = db.Column(UUID(as_uuid=True), db.ForeignKey('progress.id'))
    meta = db.Column(db.JSON, default=dict)
    current_stage = db.Column(db.String(32), default='discover')
    stage_status = db.Column(db.JSON, default=lambda: {
        'discover':'unlocked','organize':'locked','mastery':'locked','create':'locked','collaborate':'locked'
    })
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
