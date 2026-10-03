import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from .routers import companies, tags, syncs, settings, home, ipo, analyze, news, discover
from .database import engine, Base, SessionLocal
from .services.sync_runner import start_sync, run_sync, stale_company_ids, recover_interrupted_syncs
from .routers.settings import get_setting

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

_AUTO_REFRESH_INTERVAL = 300  # seconds between staleness checks


async def _auto_refresh_loop() -> None:
    """Periodically sync public companies whose last completed sync is older than the configured threshold."""
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
            to_run = []
            for company_id in stale_company_ids(db, hours):
                sync, created = start_sync(db, company_id)
                if created:
                    to_run.append(sync.id)
        except Exception:
            logger.exception("Auto-refresh check failed")
            to_run = []
        finally:
            db.close()

        if to_run:
            logger.info(f"Auto-refresh: syncing {len(to_run)} stale companies")
        for sync_id in to_run:
            await run_sync(sync_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    recover_interrupted_syncs()
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
