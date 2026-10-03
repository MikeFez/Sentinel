"""Helpers that make migrations safe to re-run.

Older versions of the entrypoint created tables with create_all() when a migration failed, without
recording a version. Such a database has some or all of the columns a migration would add, so every
step checks first; `alembic upgrade head` then works on a new, an existing, or a half-built database.
"""
import sqlalchemy as sa
from alembic import op


def has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def has_column(table: str, column: str) -> bool:
    return has_table(table) and column in {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def add_column(table: str, column: sa.Column) -> None:
    if not has_column(table, column.name):
        op.add_column(table, column)


def drop_column(table: str, column: str) -> None:
    if has_column(table, column):
        op.drop_column(table, column)
