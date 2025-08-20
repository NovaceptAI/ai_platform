import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, UniqueConstraint
from app.db import db


class UserIdentity(db.Model):
    __tablename__ = 'user_identities'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    provider = Column(Enum('google', 'facebook', 'linkedin', name='identity_provider'), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    raw_profile = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('provider', 'provider_user_id', name='uq_provider_provider_uid'),
    )
