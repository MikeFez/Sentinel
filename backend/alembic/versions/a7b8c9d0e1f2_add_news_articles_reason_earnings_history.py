"""Add news_articles table (backfilled from syncs), syncs.reason and syncs.earnings_history

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Branch_labels: None
depends_on: None
Create Date: 2026-10-03 12:00:00.000000

"""
import json
import uuid

from alembic import op
import sqlalchemy as sa

from app.migration_utils import add_column, drop_column, has_table

revision = 'a7b8c9d0e1f2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column('syncs', sa.Column('reason', sa.String(), nullable=True))
    add_column('syncs', sa.Column('earnings_history', sa.JSON(), nullable=True))
    if has_table('news_articles'):
        return  # already there (created outside migrations); nothing to backfill into
    op.create_table(
        'news_articles',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('company_id', sa.String(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('published_at', sa.Integer(), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('company_id', 'url', name='uq_news_company_url'),
    )
    op.create_index('ix_news_articles_company_id', 'news_articles', ['company_id'])
    op.create_index('ix_news_articles_published_at', 'news_articles', ['published_at'])

    # Backfill from the news already stored on syncs (oldest first, so first_seen_at is right)
    from app.services.news_store import normalize_article

    conn = op.get_bind()
    seen = set()
    rows = conn.execute(sa.text(
        "SELECT company_id, synced_at, raw_news FROM syncs WHERE raw_news IS NOT NULL ORDER BY synced_at"
    ))
    insert = sa.text(
        "INSERT INTO news_articles (id, company_id, url, title, source, summary, published_at, first_seen_at) "
        "VALUES (:id, :company_id, :url, :title, :source, :summary, :published_at, :first_seen_at)"
    )
    for company_id, synced_at, raw in rows.fetchall():
        articles = json.loads(raw) if isinstance(raw, str) else raw
        for article in articles or []:
            a = normalize_article(article)
            if not a or (company_id, a['url']) in seen:
                continue
            seen.add((company_id, a['url']))
            conn.execute(insert, {'id': str(uuid.uuid4()), 'company_id': company_id, 'first_seen_at': synced_at, **a})


def downgrade() -> None:
    op.drop_index('ix_news_articles_published_at', 'news_articles')
    op.drop_index('ix_news_articles_company_id', 'news_articles')
    op.drop_table('news_articles')
    drop_column('syncs', 'earnings_history')
    drop_column('syncs', 'reason')
