import uuid
from datetime import datetime
from app.db import db
from sqlalchemy.dialects.postgresql import UUID

class ResearchProject(db.Model):
    __tablename__ = 'research_projects'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(300))
    description = db.Column(db.Text)
    status = db.Column(db.String(32), default='active')  # active|completed|archived
    vault_folder = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProjectFile(db.Model):
    __tablename__ = 'project_files'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('research_projects.id', ondelete='CASCADE'), nullable=False)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey('uploaded_files.id', ondelete='SET NULL'))
    label = db.Column(db.String(200))
    meta = db.Column(db.JSON, default=dict)

class ResearchSession(db.Model):
    __tablename__ = 'research_sessions'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('research_projects.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)
    progress_id = db.Column(UUID(as_uuid=True), db.ForeignKey('progress.id'))
    meta = db.Column(db.JSON, default=dict)

class BrowserSearch(db.Model):
    __tablename__ = 'browser_searches'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = db.Column(UUID(as_uuid=True), db.ForeignKey('research_sessions.id', ondelete='CASCADE'), nullable=False)
    query = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(32), default='queued')  # queued|running|done|failed
    results = db.Column(db.JSON)  # list of {title, url, snippet, rank}
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ScrapeSource(db.Model):
    __tablename__ = 'scrape_sources'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = db.Column(UUID(as_uuid=True), db.ForeignKey('research_sessions.id', ondelete='CASCADE'), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    status = db.Column(db.String(32), default='queued')  # queued|running|done|failed
    content_ref = db.Column(db.String(500))  # blob key/path
    meta = db.Column(db.JSON)

class SessionNote(db.Model):
    __tablename__ = 'session_notes'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = db.Column(UUID(as_uuid=True), db.ForeignKey('research_sessions.id', ondelete='CASCADE'), nullable=False)
    note_type = db.Column(db.String(32), default='text')  # text|ai|tag|todo
    content = db.Column(db.Text)
    meta = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
