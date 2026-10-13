"""Grading the AI's sentiment calls against what the price did afterwards."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session, load_only

from ..models import Company, DailyPrice, Sync
from ..models.sync import SyncStatus


@dataclass
class Call:
    company_id: str
    at: datetime
    sentiment: str
    price: float
    model: Optional[str]
    later_price: Optional[float] = None
    later_at: Optional[datetime] = None
    # Ungraded and the horizon (plus tolerance) has passed: no price was recorded near the date
    no_data: bool = False

    @property
    def ret(self) -> Optional[float]:
        return None if self.later_price is None else (self.later_price / self.price - 1) * 100

    @property
    def hit(self) -> Optional[bool]:
        """Bullish calls are right if the price rose, bearish if it fell; neutral/mixed aren't graded."""
        if self.ret is None or self.sentiment not in ("bullish", "bearish"):
            return None
        return self.ret > 0 if self.sentiment == "bullish" else self.ret < 0


def tolerance(horizon_days: int) -> timedelta:
    """How far from the target date a price may be and still count (syncs aren't exactly daily)."""
    return timedelta(days=max(2, round(horizon_days * 0.25)))


def grade(series: list[tuple[datetime, float]], calls: list[Call], horizon_days: int, now: Optional[datetime] = None) -> list[Call]:
    """Fill in each call's later price: the point in `series` closest to call + horizon, within tolerance.

    Calls left ungraded once that window has passed are marked `no_data`; the rest are still pending.
    """
    tol = tolerance(horizon_days)
    now = now or datetime.now(timezone.utc)
    for call in calls:
        target = call.at + timedelta(days=horizon_days)
        best = min(series, key=lambda p: abs(p[0] - target), default=None)
        if best and abs(best[0] - target) <= tol and best[0] > call.at:
            call.later_at, call.later_price = best
        else:
            call.no_data = now > target + tol
    return calls


def one_per_day(calls: list[Call]) -> list[Call]:
    """Keep the last call per company per day, so a day with five syncs doesn't count five times."""
    keep: dict = {}
    for c in sorted(calls, key=lambda c: c.at):
        keep[(c.company_id, c.at.date())] = c
    return list(keep.values())


def summarize(calls: list[Call]) -> dict:
    graded = [c for c in calls if c.hit is not None]
    def avg(xs):
        xs = [x for x in xs if x is not None]
        return round(sum(xs) / len(xs), 2) if xs else None
    return {
        "calls": len(calls),
        "graded": len(graded),
        "hits": sum(1 for c in graded if c.hit),
        "hit_rate": round(100 * sum(1 for c in graded if c.hit) / len(graded), 1) if graded else None,
        "avg_return": {s: avg(c.ret for c in calls if c.sentiment == s) for s in ("bullish", "bearish", "neutral", "mixed")},
        # How often each sentiment was called (to spot a model that never calls one of them)
        "counts": {s: sum(1 for c in calls if c.sentiment == s) for s in ("bullish", "bearish", "neutral", "mixed")},
        # Not due yet, vs. due but no price was recorded near the date (e.g. Sentinel wasn't running)
        "pending": sum(1 for c in calls if c.ret is None and not c.no_data),
        "no_data": sum(1 for c in calls if c.no_data),
    }


def scorecard(db: Session, horizon_days: int, company_id: Optional[str] = None, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    companies = {
        c.id: c for c in db.query(Company).filter(Company.status == "public", Company.ticker.isnot(None))
        if company_id is None or c.id == company_id
    }
    q = (
        db.query(Sync)
        .options(load_only(Sync.company_id, Sync.synced_at, Sync.stock_price, Sync.ai_sentiment, Sync.llm_model))
        .filter(Sync.status == SyncStatus.completed, Sync.stock_price.isnot(None), Sync.company_id.in_(list(companies)))
        .order_by(Sync.synced_at)
    )
    series: dict = {}
    calls: list[Call] = []
    for s in q:
        series.setdefault(s.company_id, []).append((s.synced_at, s.stock_price))
        if s.ai_sentiment:
            calls.append(Call(s.company_id, s.synced_at, s.ai_sentiment.value, s.stock_price, s.llm_model))
    for p in db.query(DailyPrice).filter(DailyPrice.company_id.in_(list(companies))):
        series.setdefault(p.company_id, []).append((p.at, p.price))
    for c in companies.values():  # the latest quote is a price point too
        if c.quote_price is not None and c.quote_at is not None:
            series.setdefault(c.id, []).append((c.quote_at, c.quote_price))

    calls = one_per_day(calls)
    for cid in companies:
        grade(series.get(cid, []), [c for c in calls if c.company_id == cid], horizon_days, now)

    by_company = []
    for cid, company in companies.items():
        mine = [c for c in calls if c.company_id == cid]
        if mine:
            by_company.append({"company_id": cid, "name": company.name, "ticker": company.ticker, **summarize(mine)})
    models = sorted({c.model or "unknown" for c in calls})
    return {
        "horizon_days": horizon_days,
        "overall": summarize(calls),
        "by_company": sorted(by_company, key=lambda r: -r["graded"]),
        "by_model": [{"model": m, **summarize([c for c in calls if (c.model or "unknown") == m])} for m in models],
        "recent": [
            {
                "company_id": c.company_id, "name": companies[c.company_id].name, "at": c.at, "sentiment": c.sentiment,
                "price": c.price, "later_price": c.later_price, "later_at": c.later_at,
                "return": round(c.ret, 2) if c.ret is not None else None, "hit": c.hit, "model": c.model,
                "no_data": c.no_data,
            }
            for c in sorted(calls, key=lambda c: c.at, reverse=True)[:60]
        ],
    }
