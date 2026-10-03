"""Add error column to syncs table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Branch_labels: None
depends_on: None
Create Date: 2026-10-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.migration_utils import add_column, drop_column, has_table

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column('syncs', sa.Column('error', sa.Text(), nullable=True))


def downgrade() -> None:
    drop_column('syncs', 'error')
