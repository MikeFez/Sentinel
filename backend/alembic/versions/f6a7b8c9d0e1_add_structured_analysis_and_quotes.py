"""Add structured analysis columns to syncs and quote columns to companies

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Branch_labels: None
depends_on: None
Create Date: 2026-10-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.migration_utils import add_column, drop_column, has_table

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column('syncs', sa.Column('ai_key_points', sa.JSON(), nullable=True))
    add_column('syncs', sa.Column('ai_risks', sa.JSON(), nullable=True))
    add_column('syncs', sa.Column('ai_changes', sa.Text(), nullable=True))
    add_column('companies', sa.Column('quote_price', sa.Float(), nullable=True))
    add_column('companies', sa.Column('quote_change', sa.Float(), nullable=True))
    add_column('companies', sa.Column('quote_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    drop_column('companies', 'quote_at')
    drop_column('companies', 'quote_change')
    drop_column('companies', 'quote_price')
    drop_column('syncs', 'ai_changes')
    drop_column('syncs', 'ai_risks')
    drop_column('syncs', 'ai_key_points')
