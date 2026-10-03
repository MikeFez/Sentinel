"""The Activity page: what Sentinel has been doing (LLM, Finnhub and SEC calls, syncs, jobs)."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ActivityEvent, Company
from ..services import activity

router = APIRouter(prefix="/api/activity", tags=["activity"])

KINDS = ("llm", "finnhub", "sec", "sync", "job")


def _p95(values: list[int]) -> Optional[int]:
    if not values:
        return None
    values = sorted(values)
    return values[min(len(values) - 1, int(round(0.95 * (len(values) - 1))))]


@router.get("/summary")
def summary(hours: int = Query(24, ge=1, le=24 * 14), db: Session = Depends(get_db)):
    """Totals, an hourly series per kind, and per-operation stats for the last `hours`."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    events = db.query(ActivityEvent).filter(ActivityEvent.at >= since).all()

    totals = {k: {"count": 0, "errors": 0, "busy_seconds": 0.0} for k in KINDS}
    tokens = {"prompt": 0, "completion": 0}
    ops: dict = {}
    buckets = hours if hours <= 48 else hours // 24  # hourly up to 2 days, daily beyond
    bucket_seconds = 3600 if hours <= 48 else 86400
    series = {k: [0] * buckets for k in KINDS}

    for e in events:
        if e.kind not in totals:
            continue
        t = totals[e.kind]
        t["count"] += 1
        t["errors"] += e.status == "error"
        t["busy_seconds"] += e.duration_ms / 1000
        if e.kind == "llm":
            tokens["prompt"] += e.prompt_tokens or 0
            tokens["completion"] += e.completion_tokens or 0
        op = ops.setdefault((e.kind, e.name), {"kind": e.kind, "name": e.name, "count": 0, "errors": 0, "durations": [], "tokens": 0, "last_error": None, "last_at": None})
        op["count"] += 1
        op["durations"].append(e.duration_ms)
        op["tokens"] += (e.prompt_tokens or 0) + (e.completion_tokens or 0)
        if e.status == "error":
            op["errors"] += 1
            if op["last_error"] is None or e.at > op["last_error"][0]:
                op["last_error"] = (e.at, e.detail)
        op["last_at"] = max(op["last_at"] or e.at, e.at)
        index = int((e.at - since).total_seconds() // bucket_seconds)
        series[e.kind][min(max(index, 0), buckets - 1)] += 1

    operations = []
    for op in ops.values():
        d = op.pop("durations")
        last_error = op.pop("last_error")
        operations.append({
            **op,
            "avg_ms": round(sum(d) / len(d)),
            "p95_ms": _p95(d),
            "last_error": last_error[1] if last_error else None,
        })
    operations.sort(key=lambda o: (KINDS.index(o["kind"]), -o["count"]))
    for t in totals.values():
        t["busy_seconds"] = round(t["busy_seconds"], 1)

    return {
        "hours": hours,
        "since": since,
        "bucket_seconds": bucket_seconds,
        "totals": totals,
        "llm_tokens": tokens,
        "series": series,
        "operations": operations,
        "running": _named(db, activity.running()),
        "api": activity.api_stats(),
    }


@router.get("/events")
def events(
    kind: Optional[str] = None,
    errors_only: bool = False,
    company_id: Optional[str] = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    """The most recent events, newest first."""
    q = db.query(ActivityEvent)
    if kind:
        q = q.filter(ActivityEvent.kind == kind)
    if errors_only:
        q = q.filter(ActivityEvent.status == "error")
    if company_id:
        q = q.filter(ActivityEvent.company_id == company_id)
    rows = [
        {"id": e.id, "at": e.at, "kind": e.kind, "name": e.name, "status": e.status, "duration_ms": e.duration_ms,
         "company_id": e.company_id, "prompt_tokens": e.prompt_tokens, "completion_tokens": e.completion_tokens,
         "detail": e.detail}
        for e in q.order_by(ActivityEvent.at.desc()).limit(limit)
    ]
    return _named(db, rows)


def _named(db: Session, rows: list[dict]) -> list[dict]:
    """Add company names to rows that have a company_id."""
    ids = {r["company_id"] for r in rows if r.get("company_id")}
    names = {c.id: c.name for c in db.query(Company).filter(Company.id.in_(ids))} if ids else {}
    return [{**r, "company_name": names.get(r.get("company_id"))} for r in rows]
