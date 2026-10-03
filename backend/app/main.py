import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from .routers import companies, tags, syncs, settings, home, ipo, analyze, news, discover
from .database import engine, Base, SessionLocal
from .services.sync_runner import start_sync, run_sync, stale_company_ids, recover_interrupted_syncs, Thresholds
from .services.quote_service import refresh_quotes
from .services.maintenance import prune_history
from .routers.settings import get_setting, get_float
from .config import settings as app_settings

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

_AUTO_REFRESH_INTERVAL = 300  # seconds between staleness checks
_QUOTE_CHECK_INTERVAL = 60  # seconds between checks of whether quotes are due
_PRUNE_INTERVAL = 24 * 3600


async def _auto_refresh_loop() -> None:
    """Sync stale companies (public and, more slowly, private) and prune old sync detail once a day."""
    last_prune = 0.0
    while True:
        db = SessionLocal()
        to_run = []
        try:
            if time.monotonic() - last_prune > _PRUNE_INTERVAL or not last_prune:
                last_prune = time.monotonic()
                await asyncio.to_thread(prune_history, db, get_float(db, "history_detail_days"))
            if get_setting(db, "auto_refresh_enabled") == "true":
                for company_id in stale_company_ids(db, Thresholds.for_auto_refresh(db)):
                    sync, created = start_sync(db, company_id)
                    if created:
                        to_run.append(sync.id)
        except Exception:
            logger.exception("Auto-refresh check failed")
        finally:
            db.close()

        if to_run:
            logger.info(f"Auto-refresh: syncing {len(to_run)} stale companies")
        for sync_id in to_run:
            await run_sync(sync_id)
        await asyncio.sleep(_AUTO_REFRESH_INTERVAL)


async def _quote_loop() -> None:
    """Refresh quotes every price_refresh_minutes while the market is open (and once after close)."""
    last_run = 0.0
    while True:
        db = SessionLocal()
        try:
            minutes = get_float(db, "price_refresh_minutes")
            if minutes > 0 and app_settings.finnhub_api_key and time.monotonic() - last_run >= minutes * 60:
                last_run = time.monotonic()
                # Its own session: the refresh runs in a worker thread
                await asyncio.to_thread(_refresh_quotes_in_thread)
        except Exception:
            logger.exception("Quote refresh failed")
        finally:
            db.close()
        await asyncio.sleep(_QUOTE_CHECK_INTERVAL)


def _refresh_quotes_in_thread() -> None:
    db = SessionLocal()
    try:
        refresh_quotes(db, app_settings.finnhub_api_key)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    recover_interrupted_syncs()
    tasks = [asyncio.create_task(_auto_refresh_loop()), asyncio.create_task(_quote_loop())]
    yield
    for task in tasks:
        task.cancel()
    for task in tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Sentinel API", version="1.0.0", lifespan=lifespan)

# Check if frontend dist exists (for Docker deployment)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
frontend_exists = frontend_dist.exists() and frontend_dist.is_dir()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(companies.router)
app.include_router(tags.router)
app.include_router(syncs.router)
app.include_router(settings.router)
app.include_router(home.router)
app.include_router(ipo.router)
app.include_router(analyze.router)
app.include_router(news.router)
app.include_router(discover.router)


@app.get("/health")
def health():
    return {"status": "healthy"}


# Serve frontend static files in production (Docker)
if frontend_exists:
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # If requesting a file that exists, serve it
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for SPA routing
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    def root():
        return {"message": "Sentinel API is running - Frontend served separately in development"}
