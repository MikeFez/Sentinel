import os
import tempfile

# Point the app at a throwaway database before anything imports it
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ.setdefault("FINNHUB_API_KEY", "")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    from app.services import sync_runner

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    sync_runner.sync_queue = sync_runner.SyncQueue()  # the queue outlives a test otherwise
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    # Not used as a context manager, so the background loops in the lifespan don't start
    return TestClient(app)
