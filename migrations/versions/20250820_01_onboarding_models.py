"""add onboarding models and oauth identities

Revision ID: 20250820_01
Revises: 
Create Date: 2025-08-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20250820_01'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enums
    account_type = sa.Enum('learner', 'educator', 'professional', 'organization', name='account_type')
    onboarding_status = sa.Enum('pending', 'complete', name='onboarding_status')
    identity_provider = sa.Enum('google', 'facebook', 'linkedin', name='identity_provider')
    subscription_status = sa.Enum('none', 'trial', 'active', 'past_due', name='subscription_status')

    account_type.create(op.get_bind(), checkfirst=True)
    onboarding_status.create(op.get_bind(), checkfirst=True)
    identity_provider.create(op.get_bind(), checkfirst=True)
    subscription_status.create(op.get_bind(), checkfirst=True)

    # users columns
    op.add_column('users', sa.Column('account_type', account_type, nullable=True))
    op.add_column('users', sa.Column('onboarding_status', onboarding_status, server_default='pending', nullable=False))

    # learner_profiles
    op.create_table(
        'learner_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('school', sa.String(length=255), nullable=False),
        sa.Column('class_name', sa.String(length=255), nullable=False),
        sa.Column('favorite_subjects', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('hobbies', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('interests', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('extras', postgresql.JSONB, nullable=True)
    )

    # educator_profiles
    op.create_table(
        'educator_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('school', sa.String(length=255), nullable=False),
        sa.Column('subjects', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('classes_taught', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('students_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('years_experience', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('hobbies', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('extras', postgresql.JSONB, nullable=True)
    )

    # professional_profiles
    op.create_table(
        'professional_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('sector', sa.String(length=255), nullable=False),
        sa.Column('job_title', sa.String(length=255), nullable=False),
        sa.Column('designation', sa.String(length=255), nullable=False),
        sa.Column('years_experience', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skills', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('interests', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('hobbies', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('extras', postgresql.JSONB, nullable=True)
    )

    # organization_profiles
    op.create_table(
        'organization_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('org_name', sa.String(length=255), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=False),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('admin_tier', sa.String(length=50), nullable=True),
        sa.Column('subscription_status', subscription_status, nullable=False, server_default='none')
    )

    # user_identities
    op.create_table(
        'user_identities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', identity_provider, nullable=False),
        sa.Column('provider_user_id', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('raw_profile', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint('provider', 'provider_user_id', name='uq_provider_provider_uid')
    )


def downgrade() -> None:
    op.drop_table('user_identities')
    op.drop_table('organization_profiles')
    op.drop_table('professional_profiles')
    op.drop_table('educator_profiles')
    op.drop_table('learner_profiles')

    op.drop_column('users', 'onboarding_status')
    op.drop_column('users', 'account_type')

    sa.Enum(name='subscription_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='identity_provider').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='onboarding_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='account_type').drop(op.get_bind(), checkfirst=True)

