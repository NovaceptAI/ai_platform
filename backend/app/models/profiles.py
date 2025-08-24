import uuid
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy import Column, String, Integer, Enum, ForeignKey
from app.db import db


class LearnerProfile(db.Model):
    __tablename__ = 'learner_profiles'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    school = Column(String(255), nullable=False)
    class_name = Column(String(255), nullable=False)
    favorite_subjects = Column(ARRAY(String), nullable=False, default=list)
    hobbies = Column(ARRAY(String), nullable=False, default=list)
    interests = Column(ARRAY(String), nullable=False, default=list)
    extras = Column(JSONB, nullable=True)


class EducatorProfile(db.Model):
    __tablename__ = 'educator_profiles'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    school = Column(String(255), nullable=False)
    subjects = Column(ARRAY(String), nullable=False, default=list)
    classes_taught = Column(ARRAY(String), nullable=False, default=list)
    students_count = Column(Integer, nullable=False, default=0)
    years_experience = Column(Integer, nullable=False, default=0)
    hobbies = Column(ARRAY(String), nullable=False, default=list)
    extras = Column(JSONB, nullable=True)


class ProfessionalProfile(db.Model):
    __tablename__ = 'professional_profiles'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    sector = Column(String(255), nullable=False)
    job_title = Column(String(255), nullable=False)
    designation = Column(String(255), nullable=False)
    years_experience = Column(Integer, nullable=False, default=0)
    skills = Column(ARRAY(String), nullable=False, default=list)
    interests = Column(ARRAY(String), nullable=False, default=list)
    hobbies = Column(ARRAY(String), nullable=False, default=list)
    extras = Column(JSONB, nullable=True)


class OrganizationProfile(db.Model):
    __tablename__ = 'organization_profiles'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    org_name = Column(String(255), nullable=False)
    contact_email = Column(String(255), nullable=False)
    website = Column(String(255), nullable=True)
    admin_tier = Column(String(50), nullable=True)
    subscription_status = Column(
        Enum('none', 'trial', 'active', 'past_due', name='subscription_status'),
        nullable=False,
        default='none'
    )
