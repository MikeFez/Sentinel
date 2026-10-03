from datetime import datetime, timezone

from app.models import NewsArticle
from app.services.maintenance import prune_history
from app.services.news_store import normalize_article, store_articles
from tests import factories as f


def test_normalizes_finnhub_and_google_news_dates():
    assert normalize_article({"title": "A", "url": "u", "published_at": 1700000000})["published_at"] == 1700000000
    iso = normalize_article({"title": "B", "url": "u", "date": "2026-10-01T12:00:00"})
    assert iso["published_at"] == int(datetime(2026, 10, 1, 12, tzinfo=timezone.utc).timestamp())
    rfc = normalize_article({"title": "C", "url": "u", "date": "Thu, 01 Oct 2026 12:00:00 GMT"})
    assert rfc["published_at"] == iso["published_at"]
    assert normalize_article({"title": "D", "url": "u", "date": "whenever"})["published_at"] is None
    assert normalize_article({"title": "", "url": "u"}) is None


def test_articles_are_stored_once_per_company(db, client):
    c = f.company(db)
    other = f.company(db, "Other", "OTH")
    news = [{"title": "One", "url": "https://x/1", "published_at": 100}, {"title": "Two", "url": "https://x/2", "published_at": 200}]
    assert store_articles(db, c.id, news) == 2
    assert store_articles(db, c.id, news + [{"title": "Three", "url": "https://x/3", "published_at": 300}]) == 1
    assert store_articles(db, other.id, news) == 2  # same URL, different company
    db.commit()

    feed = client.get("/api/news/feed").json()
    assert len(feed) == 5
    assert [a["title"] for a in client.get(f"/api/news/feed?company_id={c.id}").json()] == ["Three", "Two", "One"]


def test_old_news_is_pruned_and_deleting_a_company_removes_its_news(db, client):
    c = f.company(db)
    now = datetime.now(timezone.utc).timestamp()
    store_articles(db, c.id, [
        {"title": "Old", "url": "o", "published_at": int(now - 86400 * 400)},
        {"title": "New", "url": "n", "published_at": int(now - 86400)},
    ])
    db.commit()
    prune_history(db, days=30)  # news kept 6x longer: 180 days
    assert [a.title for a in db.query(NewsArticle)] == ["New"]
    client.delete(f"/api/companies/{c.id}")
    assert db.query(NewsArticle).count() == 0
