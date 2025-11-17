# app/models/science_lab.py
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import db

class ScienceLabExperiment(db.Model):
    """Store virtual science lab experiments and results."""
    __tablename__ = 'science_lab_experiments'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Experiment details
    experiment_type = db.Column(db.String(100), nullable=False)  # e.g., "physics_pendulum", "chemistry_acid_base"
    experiment_title = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(50), nullable=False)  # physics, chemistry, biology

    # Simulation parameters and results
    initial_parameters = db.Column(JSONB, nullable=True)  # Starting conditions
    trial_data = db.Column(JSONB, nullable=True)  # Array of trial results
    observations = db.Column(db.Text, nullable=True)  # Student observations
    conclusions = db.Column(db.Text, nullable=True)  # Student conclusions

    # AI tutor interactions
    ai_hints = db.Column(JSONB, nullable=True)  # AI-generated hints during experiment
    ai_feedback = db.Column(JSONB, nullable=True)  # AI feedback on results and conclusions

    # Metadata
    status = db.Column(db.String(20), default='in_progress')  # in_progress, completed, shared
    is_saved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    user = db.relationship('Users', lazy='joined')

    def __repr__(self):
        return f"<ScienceLabExperiment(id={self.id}, type={self.experiment_type}, user={self.user_id})>"
