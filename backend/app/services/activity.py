"""Observability: a log of outbound calls, syncs and jobs (for the Activity page) and Prometheus metrics.

Recording must never break the thing being recorded, so every write swallows its own errors.
"""
import contextvars
import logging
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# Labels that apply to everything recorded inside a block, e.g. the company a sync is for
_context: contextvars.ContextVar[dict] = contextvars.ContextVar("activity_context", default={})

EVENTS = Counter("sentinel_events_total", "Outbound calls, syncs and job runs", ["kind", "name", "status"])
DURATION = Histogram(
    "sentinel_event_duration_seconds", "Duration of calls, syncs and jobs", ["kind", "name"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600),
)
TOKENS = Counter("sentinel_llm_tokens_total", "LLM tokens", ["name", "type"])
IN_FLIGHT = Gauge("sentinel_in_flight", "Calls running right now", ["kind"])
API_REQUESTS = Counter("sentinel_api_requests_total", "Requests to Sentinel's own API", ["route", "method", "status"])
API_LATENCY = Histogram("sentinel_api_request_seconds", "Sentinel API latency", ["route"])

# What's running right now (shown on the Activity page)
_running: dict[str, dict] = {}
_lock = threading.Lock()


@contextmanager
def context(**labels):
    """Attach labels (e.g. company_id) to everything recorded inside the block, across awaits and threads."""
    token = _context.set({**_context.get(), **labels})
    try:
        yield
    finally:
        _context.reset(token)


def current_company() -> Optional[str]:
    return _context.get().get("company_id")


class Timer:
    """Measures one operation and records it. Use `track(...)` rather than constructing it directly."""

    def __init__(self, kind: str, name: str, company_id: Optional[str]):
        self.kind, self.name, self.company_id = kind, name, company_id
        self.status, self.detail = "ok", None
        self.prompt_tokens = self.completion_tokens = None
        self.started = datetime.now(timezone.utc)
        self._t0 = time.perf_counter()
        self._id = uuid.uuid4().hex

    def fail(self, detail: str) -> None:
        self.status, self.detail = "error", (detail or "")[:500]

    def note(self, detail: str) -> None:
        if self.status == "ok":
            self.detail = (detail or "")[:500]


@contextmanager
def track(kind: str, name: str, company_id: Optional[str] = None):
    """Time and record an operation. Exceptions are recorded as errors and re-raised."""
    t = Timer(kind, name, company_id or current_company())
    with _lock:
        _running[t._id] = {"kind": kind, "name": name, "company_id": t.company_id, "started": t.started}
    IN_FLIGHT.labels(kind).inc()
    try:
        yield t
    except BaseException as e:
        t.fail(f"{type(e).__name__}: {e}")
        raise
    finally:
        IN_FLIGHT.labels(kind).dec()
        with _lock:
            _running.pop(t._id, None)
        _save(t, time.perf_counter() - t._t0)


def _save(t: Timer, seconds: float) -> None:
    try:
        EVENTS.labels(t.kind, t.name, t.status).inc()
        DURATION.labels(t.kind, t.name).observe(seconds)
        if t.prompt_tokens:
            TOKENS.labels(t.name, "prompt").inc(t.prompt_tokens)
        if t.completion_tokens:
            TOKENS.labels(t.name, "completion").inc(t.completion_tokens)
        from ..database import SessionLocal
        from ..models import ActivityEvent

        db = SessionLocal()
        try:
            db.add(ActivityEvent(
                at=t.started, kind=t.kind, name=t.name, status=t.status, duration_ms=int(seconds * 1000),
                company_id=t.company_id, prompt_tokens=t.prompt_tokens, completion_tokens=t.completion_tokens,
                detail=t.detail,
            ))
            db.commit()
        finally:
            db.close()
    except Exception as e:  # never let observability break the app
        logger.debug(f"Could not record activity: {e}")


def running() -> list[dict]:
    now = datetime.now(timezone.utc)
    with _lock:
        items = list(_running.values())
    return sorted(
        ({**r, "seconds": round((now - r["started"]).total_seconds(), 1)} for r in items),
        key=lambda r: -r["seconds"],
    )


# Sentinel's own API: kept in memory only (the UI polls often), reset on restart
_api: dict[tuple, dict] = {}


def record_api(route: str, method: str, status: int, seconds: float) -> None:
    API_REQUESTS.labels(route, method, str(status)).inc()
    API_LATENCY.labels(route).observe(seconds)
    with _lock:
        s = _api.setdefault((method, route), {"count": 0, "errors": 0, "total_ms": 0.0, "max_ms": 0.0})
        s["count"] += 1
        s["errors"] += status >= 500
        ms = seconds * 1000
        s["total_ms"] += ms
        s["max_ms"] = max(s["max_ms"], ms)


def api_stats() -> list[dict]:
    with _lock:
        items = list(_api.items())
    return sorted(
        (
            {"method": m, "route": r, "count": s["count"], "errors": s["errors"],
             "avg_ms": round(s["total_ms"] / s["count"], 1), "max_ms": round(s["max_ms"], 1)}
            for (m, r), s in items
        ),
        key=lambda x: -x["count"],
    )
