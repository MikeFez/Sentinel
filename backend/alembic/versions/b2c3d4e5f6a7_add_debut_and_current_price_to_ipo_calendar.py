"""Add debut_price and current_price to ipo_calendar table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Branch_labels: None
depends_on: None
Create Date: 2026-04-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.migration_utils import add_column, drop_column, has_table

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column('ipo_calendar', sa.Column('debut_price', sa.Float(), nullable=True))
    add_column('ipo_calendar', sa.Column('current_price', sa.Float(), nullable=True))


def downgrade() -> None:
    drop_column('ipo_calendar', 'current_price')
    drop_column('ipo_calendar', 'debut_price')
