from datetime import datetime, timedelta, timezone

from app.services.scorecard import Call, grade, one_per_day, summarize, benchmark_calls
from tests import factories as f

T0 = datetime(2026, 6, 1, 20, 0, tzinfo=timezone.utc)


def day(n, hour=20):
    return T0 + timedelta(days=n, hours=hour - 20)


def test_calls_are_graded_against_the_price_near_the_horizon():
    series = [(day(0), 100.0), (day(29), 108.0), (day(60), 90.0)]
    calls = grade(series, [Call("c", day(0), "bullish", 100.0, "m"), Call("c", day(0), "bearish", 100.0, "m")], 30)
    assert calls[0].later_price == 108.0 and round(calls[0].ret, 2) == 8.0
    assert calls[0].hit is True and calls[1].hit is False


def test_no_price_near_the_horizon_means_pending_then_no_data():
    series = [(day(0), 100.0), (day(45), 90.0)]  # 45 days is outside the ±8 day window
    [call] = grade(series, [Call("c", day(0), "bullish", 100.0, None)], 30, now=day(35))
    assert call.ret is None and call.hit is None and not call.no_data  # window still open
    [call] = grade(series, [Call("c", day(0), "bullish", 100.0, None)], 30, now=day(40))
    assert call.no_data
    s = summarize([call])
    assert s["pending"] == 0 and s["no_data"] == 1


def test_daily_prices_fill_gaps_between_syncs(client, db):
    from app.models import DailyPrice
    c = f.company(db, "Acme", "ACME")
    s = f.sync(db, c, hours_ago=24 * 40, sentiment="bullish", stock_price=100.0)
    later = s.synced_at + timedelta(days=30)
    db.add(DailyPrice(company_id=c.id, day=later.date().isoformat(), price=90.0, at=later))
    db.commit()
    [call] = client.get("/api/scorecard?horizon=30").json()["recent"]
    assert call["later_price"] == 90.0 and call["hit"] is False


def test_neutral_calls_are_not_graded_but_their_returns_are_reported():
    [call] = grade([(day(0), 100.0), (day(30), 95.0)], [Call("c", day(0), "neutral", 100.0, None)], 30)
    assert call.hit is None
    s = summarize([call])
    assert s["graded"] == 0 and s["avg_return"]["neutral"] == -5.0


def test_one_call_per_company_per_day():
    calls = [Call("c", day(0, 10), "bearish", 1, None), Call("c", day(0, 18), "bullish", 1, None), Call("d", day(0), "mixed", 1, None)]
    kept = one_per_day(calls)
    assert sorted(c.sentiment for c in kept) == ["bullish", "mixed"]


def test_scorecard_endpoint(client, db):
    c = f.company(db, "Acme", "ACME")
    for days_ago, price, sentiment in [(60, 100.0, "bullish"), (30, 110.0, "bearish"), (0, 104.0, None)]:
        s = f.sync(db, c, hours_ago=24 * days_ago, sentiment=sentiment, stock_price=price, llm_model="qwen")
    r = client.get("/api/scorecard?horizon=30").json()
    o = r["overall"]
    assert o["calls"] == 2 and o["graded"] == 2 and o["hits"] == 2 and o["hit_rate"] == 100.0
    assert r["by_model"][0]["model"] == "qwen" and r["by_company"][0]["name"] == "Acme"
    assert r["recent"][0]["sentiment"] == "bearish" and r["recent"][0]["return"] < 0


def test_no_early_grading_or_future_prices():
    c = Call("c", day(0), "bullish", 100, "m")
    grade([(day(25), 110), (day(30), 120)], [c], 30, now=day(26))
    assert c.ret is None and not c.no_data
    grade([(day(25), 110), (day(31), 120)], [c], 30, now=day(30))
    assert c.later_price == 110  # day 31 hasn't happened


def test_benchmark_uses_actual_endpoints_without_lookahead_and_missing_stays_missing():
    c = Call("c", day(0), "bullish", 100, "m", later_price=108, later_at=day(29))
    benchmark_calls([c], [(day(-1), 100), (day(1), 500), (day(29), 110), (day(30), 900)])
    assert round(c.benchmark_return, 3) == 10
    assert round(c.excess_return, 3) == -2 and c.relative_hit is False and c.hit is True
    missing = Call("c", day(0), "bearish", 100, "m", later_price=108, later_at=day(29))
    benchmark_calls([missing], [(day(-4), 100), (day(29), 110)])
    assert missing.benchmark_return is None and missing.relative_hit is None


def test_scorecard_reports_samples_intervals_and_prompt_cohorts(client, db):
    from app.models import BenchmarkPrice
    c = f.company(db)
    s = f.sync(db, c, hours_ago=24 * 60, sentiment="bullish", stock_price=100,
               llm_model="model", prompt_version="v1", analysis_horizon_days=30)
    f.sync(db, c, synced_at=s.synced_at + timedelta(days=30), stock_price=108)
    for at, price in [(s.synced_at - timedelta(hours=1), 100), (s.synced_at + timedelta(days=30), 110)]:
        db.add(BenchmarkPrice(symbol="SPY", day=at.date().isoformat(), price=price, at=at))
    db.commit()
    result = client.get("/api/scorecard?horizon=30").json()
    o = result["overall"]
    assert o["small_sample"] and o["return_samples"]["bullish"] == 1
    assert o["hit_rate_interval"][0] < 100 and o["hit_rate_interval"][1] == 100
    assert o["benchmark_graded"] == 1 and o["benchmark_hit_rate"] == 0
    assert o["avg_excess_return"]["bullish"] == -2
    assert result["by_version"][0]["prompt_version"] == "v1"
    assert result["by_version"][0]["prediction_days"] == 30


def test_one_per_day_uses_new_york_not_utc():
    # Both timestamps are June 1 in New York, although the latter is June 2 UTC.
    first = Call("c", day(0, 23), "bearish", 100, None)
    last = Call("c", day(1, 1), "bullish", 100, None)
    assert one_per_day([first, last]) == [last]
