"""Add structured analysis columns to syncs and quote columns to companies

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Branch_labels: None
depends_on: None
Create Date: 2026-10-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('syncs', sa.Column('ai_key_points', sa.JSON(), nullable=True))
    op.add_column('syncs', sa.Column('ai_risks', sa.JSON(), nullable=True))
    op.add_column('syncs', sa.Column('ai_changes', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('quote_price', sa.Float(), nullable=True))
    op.add_column('companies', sa.Column('quote_change', sa.Float(), nullable=True))
    op.add_column('companies', sa.Column('quote_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'quote_at')
    op.drop_column('companies', 'quote_change')
    op.drop_column('companies', 'quote_price')
    op.drop_column('syncs', 'ai_changes')
    op.drop_column('syncs', 'ai_risks')
    op.drop_column('syncs', 'ai_key_points')
