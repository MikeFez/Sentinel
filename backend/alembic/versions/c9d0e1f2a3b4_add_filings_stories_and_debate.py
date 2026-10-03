"""Add filings and news_stories tables, news_articles.story_id, and debate/model columns on syncs

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Branch_labels: None
depends_on: None
Create Date: 2026-10-03 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.migration_utils import add_column, drop_column, has_table

revision = 'c9d0e1f2a3b4'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column('syncs', sa.Column('llm_model', sa.String(), nullable=True))
    add_column('syncs', sa.Column('ai_bull', sa.Text(), nullable=True))
    add_column('syncs', sa.Column('ai_bear', sa.Text(), nullable=True))

    if not has_table('filings'):
        op.create_table(
            'filings',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('company_id', sa.String(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
            sa.Column('accession', sa.String(), nullable=False, unique=True),
            sa.Column('form', sa.String(), nullable=False),
            sa.Column('filed_on', sa.String(), nullable=False),
            sa.Column('items', sa.String(), nullable=True),
            sa.Column('url', sa.String(), nullable=False),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.Column('new_risks', sa.JSON(), nullable=True),
            sa.Column('risk_text', sa.Text(), nullable=True),
            sa.Column('error', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index('ix_filings_company_id', 'filings', ['company_id'])

    if not has_table('news_stories'):
        op.create_table(
            'news_stories',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('company_id', sa.String(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
            sa.Column('title', sa.Text(), nullable=False),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.Column('material', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('themes', sa.JSON(), nullable=True),
            sa.Column('first_seen_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('last_seen_at', sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index('ix_news_stories_company_id', 'news_stories', ['company_id'])

    # SQLite can't add a foreign key to an existing table; the ORM relationship is enough
    add_column('news_articles', sa.Column('story_id', sa.String(), nullable=True))


def downgrade() -> None:
    drop_column('news_articles', 'story_id')
    op.drop_table('news_stories')
    op.drop_table('filings')
    drop_column('syncs', 'ai_bear')
    drop_column('syncs', 'ai_bull')
    drop_column('syncs', 'llm_model')
