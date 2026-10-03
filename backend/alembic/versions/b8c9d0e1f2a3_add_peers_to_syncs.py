"""Add peers column to syncs

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Branch_labels: None
depends_on: None
Create Date: 2026-10-03 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.migration_utils import add_column, drop_column, has_table

revision = 'b8c9d0e1f2a3'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column('syncs', sa.Column('peers', sa.JSON(), nullable=True))


def downgrade() -> None:
    drop_column('syncs', 'peers')
