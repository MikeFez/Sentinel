"""Add syncs.started_at (queued vs. running, for restarts)

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Branch_labels: None
depends_on: None
Create Date: 2026-10-13 02:00:00.000000

"""
import sqlalchemy as sa

from app.migration_utils import add_column, drop_column

revision = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column('syncs', sa.Column('started_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    drop_column('syncs', 'started_at')
