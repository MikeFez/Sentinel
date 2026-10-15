from app.services.maintenance import prune_history
from tests import factories as f


def test_prune_clears_old_detail_but_keeps_prices_analysis_and_newest(db):
    c = f.company(db)
    evidence = {"sources": [{"id": "S1", "title": "Source", "excerpt": "Snapshot", "url": "https://example.com"}], "citations": []}
    old = f.sync(db, c, hours_ago=24 * 40, summary="old", raw_news=[{"title": "x"}], llm_prompt="p", stock_price=10.0,
                 ai_evidence=evidence, prompt_version="v1", analysis_horizon_days=30)
    recent = f.sync(db, c, hours_ago=24 * 5, raw_news=[{"title": "y"}])
    lonely = f.company(db, "Lonely", "LON")
    only = f.sync(db, lonely, hours_ago=24 * 90, raw_news=[{"title": "z"}])

    assert prune_history(db, days=30) == 1
    for s in (old, recent, only):
        db.refresh(s)
    assert old.raw_news is None and old.llm_prompt is None
    assert old.ai_summary == "old" and old.stock_price == 10.0
    assert old.ai_evidence == evidence and old.prompt_version == "v1" and old.analysis_horizon_days == 30
    assert recent.raw_news  # within 30 days
    assert only.raw_news  # each company's newest sync keeps its detail
    assert prune_history(db, days=0) == 0
