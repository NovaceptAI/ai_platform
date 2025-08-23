"""add result_json to progress

Revision ID: 20250823_01
Revises: 20250820_01
Create Date: 2025-08-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250823_01'
down_revision = '20250820_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('progress', sa.Column('result_json', postgresql.JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('progress', 'result_json')