"""Add filings.routine (8-Ks with nothing new for investors)

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Branch_labels: None
depends_on: None
Create Date: 2026-10-13 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.migration_utils import add_column, drop_column

revision = 'a3b4c5d6e7f8'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column('filings', sa.Column('routine', sa.Boolean(), nullable=False, server_default='0'))
    # Summaries written before the "Routine:" marker existed often said so in words. Items that are news
    # by definition (as in app.services.filings.MATERIAL_ITEMS) are never routine: models call earnings
    # 8-Ks "a routine earnings announcement".
    material = ["1.01", "1.02", "1.03", "1.05", "2.01", "2.02", "2.03", "2.04", "2.05", "2.06",
                "3.01", "4.01", "4.02", "5.01", "5.02"]
    excluded = " AND ".join(f"(',' || replace(coalesce(items, ''), ' ', '') || ',') NOT LIKE '%,{i},%'" for i in material)
    op.execute(f"UPDATE filings SET routine = 1 WHERE form = '8-K' AND lower(summary) LIKE '%routine%' AND {excluded}")


def downgrade() -> None:
    drop_column('filings', 'routine')
