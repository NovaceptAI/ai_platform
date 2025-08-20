# app/models/audit.py
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db import db

class Audit(db.Model):
    __tablename__ = "audit"
    id = Column(Integer, primary_key=True)
    route = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    ip = Column(String(45))
    user_agent = Column(String(256))
    user_id = Column(UUID(as_uuid=True), nullable=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    username = Column(String(120), nullable=True)   # <-- new
    auth_state = Column(String(32), nullable=False, default="no_token")
    status_code = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)