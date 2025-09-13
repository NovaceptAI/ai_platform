"""add analysis result tables

Revision ID: 20250830_02
Revises: 20250820_01
Create Date: 2025-08-30 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = '20250830_02'
down_revision = '20250820_01'
branch_labels = None
depends_on = None

def _uuid():
    return pg.UUID(as_uuid=True)

def upgrade() -> None:
    # sentiments
    op.create_table(
        'sentiments',
        sa.Column('id', _uuid(), primary_key=True),
        sa.Column('file_id', _uuid(), sa.ForeignKey('uploaded_files.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('method', sa.String(length=32)),
        sa.Column('model_version', sa.String(length=64)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('meta', pg.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column('overall_label', sa.String(length=16)),
        sa.Column('overall_score', sa.Float()),
        sa.Column('emotion_scores', pg.JSONB()),
        sa.Column('page_sentiments', pg.JSONB()),
        sa.UniqueConstraint('file_id','version', name='uq_sentiments_file_version')
    )
    op.create_index('ix_sentiments_file_id', 'sentiments', ['file_id'])

    # topics
    op.create_table(
        'topics',
        sa.Column('id', _uuid(), primary_key=True),
        sa.Column('file_id', _uuid(), sa.ForeignKey('uploaded_files.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('method', sa.String(length=32)),
        sa.Column('model_version', sa.String(length=64)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('meta', pg.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column('num_topics', sa.Integer()),
        sa.Column('coherence', sa.Float()),
        sa.Column('topics', pg.JSONB()),
        sa.Column('page_topics', pg.JSONB()),
        sa.Column('topic_graph', pg.JSONB()),
        sa.UniqueConstraint('file_id','version', name='uq_topics_file_version')
    )
    op.create_index('ix_topics_file_id', 'topics', ['file_id'])

    # segments
    op.create_table(
        'segments',
        sa.Column('id', _uuid(), primary_key=True),
        sa.Column('file_id', _uuid(), sa.ForeignKey('uploaded_files.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('method', sa.String(length=32)),
        sa.Column('model_version', sa.String(length=64)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('meta', pg.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column('num_segments', sa.Integer()),
        sa.Column('segments', pg.JSONB()),
        sa.UniqueConstraint('file_id','version', name='uq_segments_file_version')
    )
    op.create_index('ix_segments_file_id', 'segments', ['file_id'])

    # chronologies
    op.create_table(
        'chronologies',
        sa.Column('id', _uuid(), primary_key=True),
        sa.Column('file_id', _uuid(), sa.ForeignKey('uploaded_files.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('method', sa.String(length=32)),
        sa.Column('model_version', sa.String(length=64)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('meta', pg.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column('start_date', sa.Date()),
        sa.Column('end_date', sa.Date()),
        sa.Column('coverage_ratio', sa.Float()),
        sa.Column('granularity', sa.String(length=16)),
        sa.Column('events', pg.JSONB()),
        sa.UniqueConstraint('file_id','version', name='uq_chronologies_file_version')
    )
    op.create_index('ix_chronologies_file_id', 'chronologies', ['file_id'])

    # document_analysis
    op.create_table(
        'document_analysis',
        sa.Column('id', _uuid(), primary_key=True),
        sa.Column('file_id', _uuid(), sa.ForeignKey('uploaded_files.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('method', sa.String(length=32)),
        sa.Column('model_version', sa.String(length=64)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('meta', pg.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column('stats', pg.JSONB()),
        sa.Column('readability', pg.JSONB()),
        sa.Column('quality_scores', pg.JSONB()),
        sa.Column('outline', pg.JSONB()),
        sa.Column('key_points', pg.JSONB()),
        sa.Column('risks', pg.JSONB()),
        sa.Column('recommendations', pg.JSONB()),
        sa.UniqueConstraint('file_id','version', name='uq_document_analysis_file_version')
    )
    op.create_index('ix_document_analysis_file_id', 'document_analysis', ['file_id'])

def downgrade() -> None:
    for tbl in ["document_analysis","chronologies","segments","topics","sentiments"]:
        with op.batch_alter_table(tbl) as b:
            pass
        op.drop_table(tbl)