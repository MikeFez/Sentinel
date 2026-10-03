import asyncio
import json

from app.services.llm_service import LLMService


def run(llm, **kw):
    return asyncio.run(llm.analyze_company(
        company_name="Acme", ticker="ACME", status="public", stock_data={"stock_price": 10.0},
        news_articles=[{"title": "Acme wins contract"}], **kw,
    ))


class Scripted(LLMService):
    """Returns canned replies in order and records the prompts it was sent."""

    def __init__(self, replies):
        super().__init__("http://llm/v1", "m", api_key="")
        self.replies, self.prompts = list(replies), []

    async def generate(self, prompt, timeout=60, json_mode=False, purpose="other"):
        self.prompts.append(prompt)
        reply = self.replies.pop(0)
        if reply is None:
            self.last_error = "down"
        return reply


VERDICT = json.dumps({"summary": "Bull case is stronger.", "sentiment": "bullish", "key_points": [], "risks": []})


def test_debate_makes_three_calls_and_feeds_both_cases_to_the_verdict():
    llm = Scripted(["Contracts are growing.", "Margins are thin.", VERDICT])
    analysis, prompt = run(llm, debate=True)
    assert len(llm.prompts) == 3
    assert "bull case" in llm.prompts[0] and "bear case" in llm.prompts[1]
    assert "Bull case:\nContracts are growing." in llm.prompts[2] and "Bear case:\nMargins are thin." in llm.prompts[2]
    assert (analysis.bull_case, analysis.bear_case, analysis.sentiment) == ("Contracts are growing.", "Margins are thin.", "bullish")
    assert prompt == llm.prompts[2]


def test_single_mode_makes_one_call():
    llm = Scripted([VERDICT])
    analysis, _ = run(llm)
    assert len(llm.prompts) == 1 and analysis.bull_case is None


def test_a_failed_case_fails_the_analysis():
    llm = Scripted(["Contracts are growing.", None])
    analysis, _ = run(llm, debate=True)
    assert analysis is None and llm.last_error == "down"


def test_extra_context_reaches_every_prompt():
    llm = Scripted(["a", "b", VERDICT])
    run(llm, debate=True, extra_context="Recent SEC filings:\n- 8-K filed 2026-10-01: CEO resigned")
    assert all("CEO resigned" in p for p in llm.prompts)


def test_reasoning_effort_setting_is_sent(client, monkeypatch):
    import httpx

    sent = {}

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, headers=None, json=None):
            sent.update(json)
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    assert asyncio.run(LLMService("http://llm/v1", "m").generate("hi")) == "ok"
    assert "reasoning_effort" not in sent  # empty by default
    client.put("/api/settings", json={"llm_reasoning_effort": "medium"})
    asyncio.run(LLMService("http://llm/v1", "m").generate("hi"))
    assert sent["reasoning_effort"] == "medium"


def test_malformed_verdict_is_retried_once():
    llm = Scripted(["not json at all {", VERDICT])
    analysis, _ = run(llm)
    assert analysis.summary == "Bull case is stronger." and len(llm.prompts) == 2
