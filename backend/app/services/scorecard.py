"""Grading the AI's sentiment calls against what the price did afterwards."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from math import sqrt
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session, load_only

from ..models import Company, DailyPrice, Sync, BenchmarkPrice
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
    prompt_version: Optional[str] = None
    prediction_days: Optional[int] = None
    benchmark_return: Optional[float] = None

    @property
    def excess_return(self):
        return None if self.ret is None or self.benchmark_return is None else self.ret - self.benchmark_return

    @property
    def relative_hit(self):
        if self.excess_return is None or self.sentiment not in ("bullish", "bearish"):
            return None
        return self.excess_return > 0 if self.sentiment == "bullish" else self.excess_return < 0

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
        best = min((p for p in series if p[0] <= now and p[1] > 0), key=lambda p: abs(p[0] - target), default=None)
        if target > now:
            continue  # Don't grade a 30-day call early using a price from day 23.
        if best and abs(best[0] - target) <= tol and best[0] > call.at:
            call.later_at, call.later_price = best
        else:
            call.no_data = now > target + tol
    return calls


def one_per_day(calls: list[Call]) -> list[Call]:
    """Keep the last call per company per day, so a day with five syncs doesn't count five times."""
    keep: dict = {}
    for c in sorted(calls, key=lambda c: c.at):
        keep[(c.company_id, c.at.astimezone(ZoneInfo("America/New_York")).date())] = c
    return list(keep.values())


def summarize(calls: list[Call]) -> dict:
    graded = [c for c in calls if c.hit is not None]
    relative = [c for c in calls if c.relative_hit is not None]
    n = len(graded)
    interval = None
    if n:
        p, z = sum(bool(c.hit) for c in graded) / n, 1.96
        center = (p + z*z/(2*n)) / (1 + z*z/n)
        margin = z * sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
        interval = [round(100*(center-margin), 1), round(100*(center+margin), 1)]
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
        "hit_rate_interval": interval,
        "small_sample": n < 30,
        "return_samples": {s: sum(c.ret is not None for c in calls if c.sentiment == s)
                           for s in ("bullish", "bearish", "neutral", "mixed")},
        "benchmark_graded": len(relative),
        "benchmark_hit_rate": round(100 * sum(bool(c.relative_hit) for c in relative) / len(relative), 1) if relative else None,
        "avg_excess_return": {s: avg(c.excess_return for c in calls if c.sentiment == s)
                              for s in ("bullish", "bearish", "neutral", "mixed")},
    }


def benchmark_calls(calls, series):
    """Match SPY at/before both actual evaluation endpoints, within three days. No lookahead."""
    def before(at):
        return max((p for p in series if timedelta(0) <= at - p[0] <= timedelta(days=3) and p[1] > 0),
                   key=lambda p: p[0], default=None)
    for c in calls:
        if c.later_at is None:
            continue
        start, end = before(c.at), before(c.later_at)
        if start and end and end[0] > start[0]:
            c.benchmark_return = (end[1] / start[1] - 1) * 100


def scorecard(db: Session, horizon_days: int, company_id: Optional[str] = None, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    companies = {
        c.id: c for c in db.query(Company).filter(Company.status == "public", Company.ticker.isnot(None))
        if company_id is None or c.id == company_id
    }
    q = (
        db.query(Sync)
        .options(load_only(Sync.company_id, Sync.synced_at, Sync.stock_price, Sync.ai_sentiment, Sync.llm_model,
                           Sync.prompt_version, Sync.analysis_horizon_days))
        .filter(Sync.status == SyncStatus.completed, Sync.stock_price > 0, Sync.company_id.in_(list(companies)))
        .order_by(Sync.synced_at)
    )
    series: dict = {}
    calls: list[Call] = []
    for s in q:
        series.setdefault(s.company_id, []).append((s.synced_at, s.stock_price))
        if s.ai_sentiment:
            calls.append(Call(s.company_id, s.synced_at, s.ai_sentiment.value, s.stock_price, s.llm_model,
                              prompt_version=s.prompt_version, prediction_days=s.analysis_horizon_days))
    for p in db.query(DailyPrice).filter(DailyPrice.company_id.in_(list(companies))):
        series.setdefault(p.company_id, []).append((p.at, p.price))
    for c in companies.values():  # the latest quote is a price point too
        if c.quote_price is not None and c.quote_at is not None:
            series.setdefault(c.id, []).append((c.quote_at, c.quote_price))

    calls = one_per_day(calls)
    for cid in companies:
        grade(series.get(cid, []), [c for c in calls if c.company_id == cid], horizon_days, now)
    benchmark_calls(calls, [(p.at, p.price) for p in db.query(BenchmarkPrice).filter(BenchmarkPrice.symbol == "SPY")])

    by_company = []
    for cid, company in companies.items():
        mine = [c for c in calls if c.company_id == cid]
        if mine:
            by_company.append({"company_id": cid, "name": company.name, "ticker": company.ticker, **summarize(mine)})
    models = sorted({c.model or "unknown" for c in calls})
    versions = sorted({(c.model or "unknown", c.prompt_version or "legacy", c.prediction_days or 0) for c in calls})
    return {
        "horizon_days": horizon_days,
        "benchmark": "SPY",
        "tolerance_days": tolerance(horizon_days).days,
        "overall": summarize(calls),
        "by_company": sorted(by_company, key=lambda r: -r["graded"]),
        "by_model": [{"model": m, **summarize([c for c in calls if (c.model or "unknown") == m])} for m in models],
        "by_version": [{"model": m, "prompt_version": v, "prediction_days": d or None,
                        **summarize([c for c in calls if (c.model or "unknown", c.prompt_version or "legacy", c.prediction_days or 0) == (m, v, d)])}
                       for m, v, d in versions],
        "recent": [
            {
                "company_id": c.company_id, "name": companies[c.company_id].name, "at": c.at, "sentiment": c.sentiment,
                "price": c.price, "later_price": c.later_price, "later_at": c.later_at,
                "return": round(c.ret, 2) if c.ret is not None else None, "hit": c.hit, "model": c.model,
                "no_data": c.no_data,
                "prompt_version": c.prompt_version, "prediction_days": c.prediction_days,
                "benchmark_return": round(c.benchmark_return, 2) if c.benchmark_return is not None else None,
                "excess_return": round(c.excess_return, 2) if c.excess_return is not None else None,
                "relative_hit": c.relative_hit,
            }
            for c in sorted(calls, key=lambda c: c.at, reverse=True)[:60]
        ],
    }
