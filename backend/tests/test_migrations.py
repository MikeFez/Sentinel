"""`alembic upgrade head` must work on every database the app might meet."""
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.database import Base

BACKEND = Path(__file__).resolve().parent.parent


def config(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.attributes["url"] = url
    return cfg


def head() -> str:
    return ScriptDirectory.from_config(config("sqlite://")).get_current_head()


def columns(url: str) -> dict:
    insp = sa.inspect(sa.create_engine(url))
    return {t: {c["name"] for c in insp.get_columns(t)} for t in insp.get_table_names() if t != "alembic_version"}


def version(url: str) -> str:
    with sa.create_engine(url).connect() as conn:
        return conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()


def expected() -> dict:
    return {t.name: {c.name for c in t.columns} for t in Base.metadata.sorted_tables}


def assert_matches_models(url: str) -> None:
    have = columns(url)
    for table, cols in expected().items():
        assert table in have, f"missing table {table}"
        assert cols <= have[table], f"{table} is missing {cols - have[table]}"
    assert version(url) == head()


def test_brand_new_database(tmp_path):
    url = f"sqlite:///{tmp_path}/new.db"
    command.upgrade(config(url), "head")
    assert_matches_models(url)


def test_database_built_without_migrations(tmp_path):
    # What the old entrypoint fallback produced: every table, no alembic_version
    url = f"sqlite:///{tmp_path}/fallback.db"
    Base.metadata.create_all(sa.create_engine(url))
    command.upgrade(config(url), "head")
    assert_matches_models(url)


def test_half_migrated_database_without_a_version(tmp_path):
    url = f"sqlite:///{tmp_path}/half.db"
    command.upgrade(config(url), "d4e5f6a7b8c9")
    with sa.create_engine(url).begin() as conn:
        conn.execute(sa.text("DROP TABLE alembic_version"))
    command.upgrade(config(url), "head")
    assert_matches_models(url)


def test_existing_database_continues_from_its_version(tmp_path):
    url = f"sqlite:///{tmp_path}/old.db"
    command.upgrade(config(url), "c3d4e5f6a7b8")
    with sa.create_engine(url).begin() as conn:
        conn.execute(sa.text("INSERT INTO companies (id, name, status) VALUES ('1', 'Acme', 'public')"))
        conn.execute(sa.text(
            "INSERT INTO syncs (id, company_id, status, raw_news) VALUES "
            "('s1', '1', 'completed', '[{\"title\": \"Hello\", \"url\": \"https://x\", \"published_at\": 100}]')"
        ))
    command.upgrade(config(url), "head")
    assert_matches_models(url)
    with sa.create_engine(url).connect() as conn:
        assert conn.execute(sa.text("SELECT name FROM companies")).scalar() == "Acme"
        assert conn.execute(sa.text("SELECT title FROM news_articles")).scalar() == "Hello"  # backfilled
