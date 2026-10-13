"""Add research_items table (saved Research analyses and discoveries)

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Branch_labels: None
depends_on: None
Create Date: 2026-10-13 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.migration_utils import has_table

revision = 'b4c5d6e7f8a9'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    if has_table('research_items'):
        return
    op.create_table(
        'research_items',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
    )
    op.create_index('ix_research_items_kind', 'research_items', ['kind'])
    op.create_index('ix_research_items_created_at', 'research_items', ['created_at'])


def downgrade() -> None:
    op.drop_table('research_items')
