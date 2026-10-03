"""Add total_shares_value to ipo_calendar table

Revision ID: a1b2c3d4e5f6
Revises: fc37d3c5face
Branch_labels: None
depends_on: None
Create Date: 2026-04-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.migration_utils import add_column, drop_column, has_table

revision = 'a1b2c3d4e5f6'
down_revision = 'fc37d3c5face'
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column('ipo_calendar', sa.Column('total_shares_value', sa.Float(), nullable=True))


def downgrade() -> None:
    drop_column('ipo_calendar', 'total_shares_value')
