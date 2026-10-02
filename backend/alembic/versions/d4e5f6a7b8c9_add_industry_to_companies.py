"""Add industry column to companies table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Branch_labels: None
depends_on: None
Create Date: 2026-04-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('industry', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'industry')
