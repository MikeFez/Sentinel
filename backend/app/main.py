import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from .routers import companies, tags, syncs, settings, home, ipo, analyze, news, discover
from .database import engine, Base, SessionLocal
from .models import Company, Sync
from .models.sync import SyncStatus
from .services.sync_service import SyncService
from .config import settings as app_settings
from .routers.settings import get_setting

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

_AUTO_REFRESH_INTERVAL = 300  # seconds between staleness checks


async def _auto_refresh_loop() -> None:
    """Periodically sync companies whose last completed sync is older than the configured threshold."""
    while True:
        await asyncio.sleep(_AUTO_REFRESH_INTERVAL)
        db = SessionLocal()
        try:
            if get_setting(db, "auto_refresh_enabled") != "true":
                continue

            try:
                hours = float(get_setting(db, "auto_refresh_hours"))
            except ValueError:
                hours = 24.0

            cutoff = datetime.utcnow() - timedelta(hours=hours)

            # IDs of companies with an active sync in progress
            syncing_ids = {
                row[0]
                for row in db.query(Sync.company_id)
                .filter(Sync.status == SyncStatus.syncing)
                .distinct()
                .all()
            }

            # IDs of companies with a completed sync since the cutoff
            fresh_ids = {
                row[0]
                for row in db.query(Sync.company_id)
                .filter(Sync.status == SyncStatus.completed, Sync.synced_at >= cutoff)
                .distinct()
                .all()
            }

            excluded = syncing_ids | fresh_ids
            stale_ids = [
                row[0]
                for row in db.query(Company.id)
                .filter(Company.status == "public", Company.ticker.isnot(None))
                .all()
                if row[0] not in excluded
            ]

            if not stale_ids:
                continue

            logger.info(f"Auto-refresh: triggering sync for {len(stale_ids)} stale companies")

            llm_base_url = get_setting(db, "llm_base_url")
            llm_model = get_setting(db, "llm_model")
            news_count = int(get_setting(db, "news_count"))
        finally:
            db.close()

        for company_id in stale_ids:
            sync_db = SessionLocal()
            try:
                sync = Sync(company_id=company_id, status=SyncStatus.syncing)
                sync_db.add(sync)
                sync_db.commit()
                sync_db.refresh(sync)
                service = SyncService(sync_db, llm_base_url, llm_model, app_settings.finnhub_api_key)
                await service.sync_company(company_id, news_count=news_count, existing_sync=sync)
            except Exception as exc:
                logger.error(f"Auto-refresh failed for company {company_id}: {exc}")
            finally:
                sync_db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_auto_refresh_loop())
    yield
    task.cancel()
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
