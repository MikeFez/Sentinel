"""Add activity_events table (observability)

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Branch_labels: None
depends_on: None
Create Date: 2026-10-03 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.migration_utils import has_table

revision = 'd0e1f2a3b4c5'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    if has_table('activity_events'):
        return
    op.create_table(
        'activity_events',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('at', sa.DateTime(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
    )
    op.create_index('ix_activity_events_at', 'activity_events', ['at'])
    op.create_index('ix_activity_events_kind', 'activity_events', ['kind'])
    op.create_index('ix_activity_events_company_id', 'activity_events', ['company_id'])


def downgrade() -> None:
    op.drop_table('activity_events')
