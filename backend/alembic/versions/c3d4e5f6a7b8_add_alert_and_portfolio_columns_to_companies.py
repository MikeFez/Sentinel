"""Add alert_above, alert_below, shares_owned to companies table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Branch_labels: None
depends_on: None
Create Date: 2026-04-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.migration_utils import add_column, drop_column, has_table

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column('companies', sa.Column('alert_above', sa.Float(), nullable=True))
    add_column('companies', sa.Column('alert_below', sa.Float(), nullable=True))
    add_column('companies', sa.Column('shares_owned', sa.Float(), nullable=True))


def downgrade() -> None:
    drop_column('companies', 'shares_owned')
    drop_column('companies', 'alert_below')
    drop_column('companies', 'alert_above')
