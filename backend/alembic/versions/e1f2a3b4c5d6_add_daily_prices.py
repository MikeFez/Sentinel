"""Add daily_prices table (one price per company per trading day, for the scorecard)

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Branch_labels: None
depends_on: None
Create Date: 2026-10-13 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.migration_utils import has_table

revision = 'e1f2a3b4c5d6'
down_revision = 'd0e1f2a3b4c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not has_table('daily_prices'):
        op.create_table(
            'daily_prices',
            sa.Column('company_id', sa.String(), sa.ForeignKey('companies.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('day', sa.String(), primary_key=True),
            sa.Column('price', sa.Float(), nullable=False),
            sa.Column('at', sa.DateTime(), nullable=False),
        )
    # Seed from the price of each day's last completed sync, so existing history counts too.
    # New York days are approximated as UTC-4 (exact enough for syncs, which mostly run in daytime).
    op.execute("""
        INSERT OR IGNORE INTO daily_prices (company_id, day, price, at)
        SELECT s.company_id, date(datetime(s.synced_at, '-4 hours')), s.stock_price, s.synced_at
        FROM syncs s
        WHERE s.status = 'completed' AND s.stock_price IS NOT NULL
          AND s.synced_at = (
            SELECT max(s2.synced_at) FROM syncs s2
            WHERE s2.company_id = s.company_id AND s2.status = 'completed' AND s2.stock_price IS NOT NULL
              AND date(datetime(s2.synced_at, '-4 hours')) = date(datetime(s.synced_at, '-4 hours'))
          )
    """)


def downgrade() -> None:
    op.drop_table('daily_prices')
