import asyncio
import json
from datetime import datetime, timedelta, timezone

from app.models import NewsArticle, NewsStory
from app.services.news_store import store_articles
from app.services.stories import group_new_articles, parse_reply, theme_trends
from tests import factories as f


class Reply:
    """An LLM stand-in that returns one canned reply and keeps the prompt."""

    def __init__(self, reply):
        self.reply, self.prompt, self.last_error = reply, None, None

    async def generate(self, prompt, timeout=60, json_mode=False):
        self.prompt = prompt
        if self.reply is None:
            self.last_error = "down"
        return self.reply


def test_parse_reply_tolerates_noise():
    assert parse_reply('<think>x</think>```json\n{"stories": [{"articles": ["A1"]}, {"bad": 1}]}\n```') == [{"articles": ["A1"]}]
    assert parse_reply("nope") == []


def test_grouping_creates_stories_and_reuses_them(db):
    c = f.company(db)
    store_articles(db, c.id, [
        {"title": "Acme wins Navy deal", "url": "u1", "source": "Reuters", "published_at": 3},
        {"title": "Navy picks Acme", "url": "u2", "source": "Bloomberg", "published_at": 2},
        {"title": "5 stocks to watch", "url": "u3", "published_at": 1},
    ])
    db.commit()
    llm = Reply(json.dumps({"stories": [
        {"existing": None, "title": "Acme wins Navy contract", "summary": "A $2B deal.", "material": True,
         "themes": ["Defense contracts"], "articles": ["A1", "A2"]},
        {"existing": None, "title": "Stocks to watch", "material": False, "themes": [], "articles": ["A3"]},
    ]}))
    assert asyncio.run(group_new_articles(db, llm, c.id, "Acme")) == 3
    navy = db.query(NewsStory).filter_by(title="Acme wins Navy contract").one()
    assert navy.material and navy.themes == ["Defense contracts"] and len(navy.articles) == 2

    # A later article about the same event joins the existing story, and known themes are offered
    store_articles(db, c.id, [{"title": "More on the Navy deal", "url": "u4", "published_at": 4}])
    db.commit()
    llm2 = Reply(json.dumps({"stories": [{"existing": "S1", "articles": ["A1"], "material": False}]}))
    asyncio.run(group_new_articles(db, llm2, c.id, "Acme"))
    assert "Defense contracts" in llm2.prompt and "S1:" in llm2.prompt
    db.refresh(navy)
    assert len(navy.articles) == 3 and navy.material  # stays material


def test_llm_failure_leaves_articles_unassigned(db):
    c = f.company(db)
    store_articles(db, c.id, [{"title": "x", "url": "u"}])
    db.commit()
    assert asyncio.run(group_new_articles(db, Reply(None), c.id, "Acme")) == 0
    assert db.query(NewsArticle).one().story_id is None


def test_theme_trends(db):
    c = f.company(db)
    now = datetime.now(timezone.utc)
    for weeks_ago, theme in [(7, "Old"), (1, "SpaceX"), (0, "SpaceX"), (0, "SpaceX"), (5, "SpaceX")]:
        db.add(NewsStory(company_id=c.id, title="t", themes=[theme], material=True, first_seen_at=now - timedelta(weeks=weeks_ago, hours=1)))
    db.add(NewsStory(company_id=c.id, title="recap", themes=["Market recap"], material=False, first_seen_at=now))
    db.commit()
    trends = theme_trends(db, c.id, weeks=8, now=now)
    spacex = trends[0]
    assert spacex["theme"] == "SpaceX" and spacex["total"] == 4 and spacex["rising"] is True
    assert len(spacex["weekly"]) == 8
    assert "Market recap" not in [t["theme"] for t in trends]
