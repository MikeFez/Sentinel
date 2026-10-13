import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from .routers import companies, tags, syncs, settings, home, ipo, analyze, news, discover, transfer, insights, research, notifications, activity as activity_router
from .database import SessionLocal
from .services import notifier
from .services.sync_runner import queue_sync, sync_queue, stale_company_ids, recover_interrupted_syncs, Thresholds
from .services.quote_service import refresh_quotes
from .services.maintenance import prune_history
from .services.events import due_event_syncs, due_signal_syncs
from .services.filings import check_filings
from .services.llm_service import LLMService
from .services import activity
from .routers.settings import get_setting, get_float
from .config import settings as app_settings

logger = logging.getLogger(__name__)

# The schema is managed by Alembic only (docker-entrypoint.sh runs `alembic upgrade head`)

_AUTO_REFRESH_INTERVAL = 300  # seconds between staleness checks
_QUOTE_CHECK_INTERVAL = 60  # seconds between checks of whether quotes are due
_PRUNE_INTERVAL = 24 * 3600


async def _auto_refresh_loop() -> None:
    """Sync stale companies (public and, more slowly, private) and prune old sync detail once a day."""
    last_prune = 0.0
    while True:
        db = SessionLocal()
        wanted: list = []
        try:
            if time.monotonic() - last_prune > _PRUNE_INTERVAL or not last_prune:
                last_prune = time.monotonic()
                with activity.track("job", "prune") as t:
                    n = await asyncio.to_thread(prune_history, db, get_float(db, "history_detail_days"))
                    t.note(f"pruned {n}")
            wanted = due_event_syncs(
                db, get_float(db, "move_sync_percent"), get_setting(db, "earnings_sync") == "true",
                drift_threshold=get_float(db, "analysis_drift_percent"),
            )
            if get_setting(db, "signal_sync") == "true" and app_settings.finnhub_api_key:
                with activity.track("job", "analyst & insider check") as t:
                    signals = await asyncio.to_thread(_signal_syncs_in_thread)
                    t.note(f"{len(signals)} triggered")
                wanted += signals
            if get_setting(db, "auto_refresh_enabled") == "true":
                wanted += [(cid, "Scheduled refresh") for cid in stale_company_ids(db, Thresholds.for_auto_refresh(db))]
        except Exception:
            logger.exception("Auto-refresh check failed")
        finally:
            db.close()

        # New SEC filings first, so their summaries reach the analyses queued below
        await _check_filings()
        await asyncio.to_thread(notifier.maybe_send_digest)
        db = SessionLocal()
        try:
            created = sum(queue_sync(db, company_id, reason)[1] for company_id, reason in wanted)
            if created:
                logger.info(f"Auto-refresh: queued {created} sync(s)")
        except Exception:
            logger.exception("Auto-refresh: queueing syncs failed")
        finally:
            db.close()
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


async def _check_filings() -> None:
    db = SessionLocal()
    try:
        enabled = get_setting(db, "filings_enabled") == "true"
        llm = LLMService(get_setting(db, "llm_base_url"), get_setting(db, "llm_model"))
    finally:
        db.close()
    if not enabled:
        return
    try:
        with activity.track("job", "SEC filings check") as t:
            saved = await check_filings(SessionLocal, llm)
            t.note(f"{saved} new")
        if saved:
            logger.info(f"Summarized {saved} new SEC filing(s)")
    except Exception:
        logger.exception("SEC filings check failed")


def _signal_syncs_in_thread() -> list:
    db = SessionLocal()
    try:
        return due_signal_syncs(db, app_settings.finnhub_api_key)
    finally:
        db.close()


def _refresh_quotes_in_thread() -> None:
    db = SessionLocal()
    try:
        with activity.track("job", "quote refresh") as t:
            t.note(f"{refresh_quotes(db, app_settings.finnhub_api_key)} updated")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    recover_interrupted_syncs()
    tasks = [
        asyncio.create_task(sync_queue.worker()),
        asyncio.create_task(_auto_refresh_loop()),
        asyncio.create_task(_quote_loop()),
    ]
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

@app.middleware("http")
async def record_api_requests(request, call_next):
    """Count and time requests to /api (shown on the Activity page and in /metrics)."""
    if not request.url.path.startswith("/api"):
        return await call_next(request)
    t0 = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        activity.record_api(getattr(route, "path", "unmatched"), request.method, status, time.perf_counter() - t0)


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Prometheus metrics: outbound calls, LLM tokens, syncs, jobs, API requests."""
    from fastapi import Response
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


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
app.include_router(transfer.router)
app.include_router(insights.router)
app.include_router(activity_router.router)
app.include_router(research.router)
app.include_router(notifications.router)


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
