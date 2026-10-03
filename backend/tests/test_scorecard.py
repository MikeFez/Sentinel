from datetime import datetime, timedelta, timezone

from app.services.scorecard import Call, grade, one_per_day, summarize
from tests import factories as f

T0 = datetime(2026, 6, 1, 20, 0, tzinfo=timezone.utc)


def day(n, hour=20):
    return T0 + timedelta(days=n, hours=hour - 20)


def test_calls_are_graded_against_the_price_near_the_horizon():
    series = [(day(0), 100.0), (day(29), 108.0), (day(60), 90.0)]
    calls = grade(series, [Call("c", day(0), "bullish", 100.0, "m"), Call("c", day(0), "bearish", 100.0, "m")], 30)
    assert calls[0].later_price == 108.0 and round(calls[0].ret, 2) == 8.0
    assert calls[0].hit is True and calls[1].hit is False


def test_no_price_near_the_horizon_means_pending():
    [call] = grade([(day(0), 100.0), (day(45), 90.0)], [Call("c", day(0), "bullish", 100.0, None)], 30)
    assert call.ret is None and call.hit is None  # 45 days is outside the ±8 day window


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
