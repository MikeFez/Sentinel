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


def test_daily_prices_are_seeded_from_each_days_last_sync(tmp_path):
    url = f"sqlite:///{tmp_path}/prices.db"
    command.upgrade(config(url), "d0e1f2a3b4c5")
    with sa.create_engine(url).begin() as conn:
        conn.execute(sa.text("INSERT INTO companies (id, name, status) VALUES ('1', 'Acme', 'public')"))
        conn.execute(sa.text(
            "INSERT INTO syncs (id, company_id, status, stock_price, synced_at) VALUES "
            "('a', '1', 'completed', 10.0, '2026-06-01 14:00:00'),"
            "('b', '1', 'completed', 11.0, '2026-06-01 19:00:00'),"  # same New York day, later: kept
            "('c', '1', 'failed', 99.0, '2026-06-01 20:00:00'),"
            "('d', '1', 'completed', 12.0, '2026-06-02 15:00:00')"
        ))
    command.upgrade(config(url), "head")
    with sa.create_engine(url).connect() as conn:
        rows = conn.execute(sa.text("SELECT day, price FROM daily_prices ORDER BY day")).all()
    assert [tuple(r) for r in rows] == [("2026-06-01", 11.0), ("2026-06-02", 12.0)]


def test_routine_8ks_are_backfilled_from_their_summaries(tmp_path):
    url = f"sqlite:///{tmp_path}/filings.db"
    command.upgrade(config(url), "f2a3b4c5d6e7")
    with sa.create_engine(url).begin() as conn:
        conn.execute(sa.text("INSERT INTO companies (id, name, status) VALUES ('1', 'Acme', 'public')"))
        conn.execute(sa.text(
            "INSERT INTO filings (id, company_id, accession, form, filed_on, url, summary) VALUES "
            "('a', '1', 'x1', '8-K', '2026-08-13', 'u', 'It is routine supplemental disclosure.'),"
            "('b', '1', 'x2', '8-K', '2026-09-15', 'u', 'A financing update for the acquisition.'),"
            "('c', '1', 'x3', '10-Q', '2026-08-10', 'u', 'Routine quarter.')"
        ))
        conn.execute(sa.text(
            "INSERT INTO filings (id, company_id, accession, form, filed_on, url, summary, items) VALUES "
            "('d', '1', 'x4', '8-K', '2026-08-06', 'u', 'Q2 results. It is a routine earnings announcement.', '2.02,9.01')"
        ))
    command.upgrade(config(url), "head")
    with sa.create_engine(url).connect() as conn:
        rows = dict(conn.execute(sa.text("SELECT id, routine FROM filings")).all())
    assert rows == {"a": 1, "b": 0, "c": 0, "d": 0}
