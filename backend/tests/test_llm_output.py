"""How generate() handles the output budget and replies with no answer."""
import asyncio

import httpx

from app.services.llm_service import LLMService


def fake_server(monkeypatch, replies):
    """Serve `replies` (status, json) in order; returns the request bodies sent."""
    sent = []

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, headers=None, json=None):
            sent.append(dict(json))
            status, body = replies.pop(0)
            return httpx.Response(status, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    return sent


def answer(content, finish="stop"):
    return 200, {"choices": [{"message": {"content": content}, "finish_reason": finish}],
                 "usage": {"completion_tokens": 4096}}


def test_reasoning_that_uses_up_the_budget_is_a_failure_with_a_clear_error(monkeypatch):
    fake_server(monkeypatch, [answer("", finish="length")])
    llm = LLMService("http://llm/v1", "m", reasoning_effort="")
    assert asyncio.run(llm.generate("hi")) is None
    assert "ran out of output tokens (4096)" in llm.last_error


def test_empty_answer_is_a_failure(monkeypatch):
    fake_server(monkeypatch, [answer("<think>hmm</think>")])
    llm = LLMService("http://llm/v1", "m", reasoning_effort="")
    assert asyncio.run(llm.generate("hi")) is None and llm.last_error == "The LLM returned an empty answer"


def test_max_tokens_is_sent_and_dropped_if_the_server_rejects_it(monkeypatch):
    sent = fake_server(monkeypatch, [(400, {"error": "bad"}), (400, {"error": "max_tokens too large"}), answer("ok")])
    llm = LLMService("http://llm/v1", "m", reasoning_effort="")
    llm.max_tokens = 16384
    assert asyncio.run(llm.generate("hi", json_mode=True)) == "ok"
    assert sent[0]["max_tokens"] == 16384 and "response_format" in sent[0]
    assert "response_format" not in sent[1] and "max_tokens" in sent[1]
    assert "max_tokens" not in sent[2]


def test_analysis_retries_once_after_an_empty_answer(monkeypatch):
    verdict = '{"summary": "Fine.", "sentiment": "bearish", "key_points": [], "risks": [], "changes": null}'
    sent = fake_server(monkeypatch, [answer(""), answer(verdict)])
    llm = LLMService("http://llm/v1", "m", reasoning_effort="")
    analysis, _ = asyncio.run(llm.analyze_company("Acme", "ACME", "public", None, []))
    assert analysis.sentiment == "bearish" and len(sent) == 2
