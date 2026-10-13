"""Add notifications table (what was sent, so each event is sent once)

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Branch_labels: None
depends_on: None
Create Date: 2026-10-13 05:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.migration_utils import has_table

revision = 'c5d6e7f8a9b0'
down_revision = 'b4c5d6e7f8a9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    if has_table('notifications'):
        return
    op.create_table(
        'notifications',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('key', sa.String(), nullable=False, unique=True),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), sa.ForeignKey('companies.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_notifications_company_id', 'notifications', ['company_id'])
    op.create_index('ix_notifications_at', 'notifications', ['at'])


def downgrade() -> None:
    op.drop_table('notifications')
