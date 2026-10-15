"""Persist inbox reviews, analysis evidence and evaluation metadata, and benchmark prices."""
from alembic import op
import sqlalchemy as sa
from app.migration_utils import add_column, drop_column, has_table

revision = "d6e7f8a9b0c1"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade():
    add_column("syncs", sa.Column("ai_evidence", sa.JSON(), nullable=True))
    add_column("syncs", sa.Column("prompt_version", sa.String(), nullable=True))
    add_column("syncs", sa.Column("analysis_horizon_days", sa.Integer(), nullable=True))
    if not has_table("inbox_reviews"):
        op.create_table("inbox_reviews",
            sa.Column("key", sa.String(), primary_key=True),
            sa.Column("company_id", sa.String(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("snoozed_until", sa.DateTime(), nullable=True))
    if not has_table("benchmark_prices"):
        op.create_table("benchmark_prices",
            sa.Column("symbol", sa.String(), primary_key=True),
            sa.Column("day", sa.String(), primary_key=True),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("at", sa.DateTime(), nullable=False))


def downgrade():
    op.drop_table("benchmark_prices")
    op.drop_table("inbox_reviews")
    for col in ("analysis_horizon_days", "prompt_version", "ai_evidence"):
        drop_column("syncs", col)
