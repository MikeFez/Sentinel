"""Create the base tables (the schema before the first column migrations)

The migration chain used to start by adding columns to tables that only existed because the
app created them, so a brand-new database couldn't be migrated. This creates them first.

Revision ID: 0001_initial
Revises:
Create Date: 2026-02-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.migration_utils import has_table

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not has_table('companies'):
        op.create_table(
            'companies',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('ticker', sa.String(), nullable=True),
            sa.Column('status', sa.Enum('public', 'pre_ipo', 'private', 'acquired', name='companystatus'), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('website', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
    if not has_table('tags'):
        op.create_table(
            'tags',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('name', sa.String(), nullable=False, unique=True),
            sa.Column('color', sa.String(), nullable=False),
        )
    if not has_table('company_tags'):
        op.create_table(
            'company_tags',
            sa.Column('company_id', sa.String(), sa.ForeignKey('companies.id'), primary_key=True),
            sa.Column('tag_id', sa.String(), sa.ForeignKey('tags.id'), primary_key=True),
        )
    if not has_table('syncs'):
        op.create_table(
            'syncs',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('company_id', sa.String(), sa.ForeignKey('companies.id'), nullable=False),
            sa.Column('synced_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('stock_price', sa.Float(), nullable=True),
            sa.Column('price_change', sa.Float(), nullable=True),
            sa.Column('market_cap', sa.String(), nullable=True),
            sa.Column('pe_ratio', sa.Float(), nullable=True),
            sa.Column('volume', sa.Integer(), nullable=True),
            sa.Column('fifty_two_wk_hi', sa.Float(), nullable=True),
            sa.Column('fifty_two_wk_lo', sa.Float(), nullable=True),
            sa.Column('raw_news', sa.JSON(), nullable=True),
            sa.Column('ai_summary', sa.Text(), nullable=True),
            sa.Column('ai_sentiment', sa.Enum('bullish', 'bearish', 'neutral', 'mixed', name='sentimenttype'), nullable=True),
            sa.Column('status', sa.Enum('pending', 'syncing', 'completed', 'failed', name='syncstatus'), nullable=False),
        )
    if not has_table('settings'):
        op.create_table(
            'settings',
            sa.Column('key', sa.String(), primary_key=True),
            sa.Column('value', sa.String(), nullable=False),
        )
    if not has_table('ipo_calendar'):
        op.create_table(
            'ipo_calendar',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('symbol', sa.String(), nullable=True),
            sa.Column('date', sa.String(), nullable=False),
            sa.Column('price_range_low', sa.Float(), nullable=True),
            sa.Column('price_range_high', sa.Float(), nullable=True),
            sa.Column('shares', sa.Integer(), nullable=True),
            sa.Column('exchange', sa.String(), nullable=True),
            sa.Column('status', sa.String(), nullable=True),
            sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now()),
        )


def downgrade() -> None:
    for table in ('ipo_calendar', 'settings', 'syncs', 'company_tags', 'tags', 'companies'):
        op.drop_table(table)
