from app.services.events import analyst_reason, insider_reason


def ratings(buy, hold, sell, strong_buy=0, strong_sell=0):
    return {"buy": buy, "hold": hold, "sell": sell, "strong_buy": strong_buy, "strong_sell": strong_sell}


def test_small_analyst_drift_is_ignored():
    assert analyst_reason(ratings(14, 5, 0, 7), ratings(15, 5, 0, 7)) is None
    assert analyst_reason(None, ratings(1, 1, 1)) is None
    assert analyst_reason(ratings(1, 1, 1), ratings(1, 1, 1)) is None


def test_analyst_shift_or_consensus_flip_triggers():
    assert analyst_reason(ratings(14, 5, 0, 7), ratings(12, 7, 1, 7)) == "Analyst ratings changed: buy 21→19, hold 5→7, sell 0→1"
    # Only two ratings moved, but the consensus flipped from hold to buy
    assert analyst_reason(ratings(4, 5, 0), ratings(6, 4, 0)) is not None


def trade(name, change, code, price=10.0, date="2026-10-01"):
    return {"name": name, "change": change, "transactionCode": code, "transactionPrice": price, "transactionDate": date}


def test_large_new_open_market_trade_triggers():
    old = [trade("JANE DOE", -200_000, "S")]
    new = old + [trade("ADAM SPICE", -150_000, "S"), trade("BOB", 20_000, "P"), trade("CEO", 500_000, "M")]
    assert insider_reason(old, new, None) == "Insider Adam Spice sold 150,000 shares (~$1.5M)"


def test_known_small_or_non_market_trades_are_ignored():
    old = [trade("JANE DOE", -200_000, "S")]
    assert insider_reason(old, old, None) is None  # already seen
    assert insider_reason([], [trade("BOB", 50_000, "P")], None) is None  # $500k
    assert insider_reason([], [trade("CEO", 1_000_000, "A")], None) is None  # a grant, not a trade
    # No transaction price: falls back to the current price
    assert "bought" in insider_reason([], [trade("BOB", 50_000, "P", price=None)], 30.0)
