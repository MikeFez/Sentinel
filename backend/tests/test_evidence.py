import json

from app.services.evidence import source_catalog, validated_evidence
from app.services.llm_service import Analysis, parse_analysis, prompt_version, LLMService
from tests import factories as f


def test_citations_only_resolve_known_sources_and_valid_claim_indices():
    sources = source_catalog([{"title": "Contract", "url": "https://example.com/contract"}], {"stock_price": 12})
    analysis = Analysis("A contract was announced.", "bullish", ["Price is 12"], ["Risk"])
    analysis.citations = [
        {"section": "summary", "index": 0, "source_ids": ["S1", "invented", "S1", {"url": "https://bad"}]},
        {"section": "key_points", "index": 0, "source_ids": ["S2"]},
        {"section": "risks", "index": 5, "source_ids": ["S1"]},
        {"section": [], "index": 0, "source_ids": ["S1"]},
        {"section": "risks", "index": True, "source_ids": ["S1"]},
        {"section": "summary", "index": 0, "source_ids": "S1"}, None,
    ]
    evidence = validated_evidence(analysis, sources)
    assert evidence["citations"] == [{"section": "summary", "index": 0, "source_ids": ["S1"]},
                                     {"section": "key_points", "index": 0, "source_ids": ["S2"]}]


def test_unsafe_links_are_removed_and_uncited_claims_stay_uncited():
    sources = source_catalog([{"title": "Headline", "url": "javascript:alert(1)"}])
    assert sources[0]["url"] is None
    assert validated_evidence(Analysis("An inference.", "neutral"), sources)["citations"] == []


def test_json_citations_and_versioned_prompt_with_explicit_horizon():
    payload = {"summary": "News.", "sentiment": "bullish", "citations": [
        {"section": "summary", "index": 0, "source_ids": ["S1"]}]}
    analysis = parse_analysis(json.dumps(payload))
    assert analysis.citations == payload["citations"]
    assert prompt_version("Focus on cash flow", False) != prompt_version("Focus on revenue", False)
    assert prompt_version("Focus on cash flow", False) != prompt_version("Focus on cash flow", True)
    llm = LLMService("http://llm/v1", "test")
    sources = source_catalog([{"title": "News", "url": "https://example.com"}])
    prompt = llm._build_analysis_prompt("Acme", "ACME", "public", None, [], evidence_sources=sources)
    assert "30 calendar days" in prompt and '"id": "S1"' in prompt


def test_sync_persists_evidence_and_metadata_and_api_exposes_it(client, db):
    from tests.test_sync_service import FakeLLM, run
    company = f.company(db)
    analysis = Analysis("Contract signed.", "bullish", citations=[
        {"section": "summary", "index": 0, "source_ids": ["S1"]}])
    sync = run(db, company, FakeLLM(analysis))
    result = client.get(f"/api/syncs/{sync.id}").json()
    assert result["analysis_horizon_days"] == 30
    assert result["prompt_version"].startswith("evidence-v1-")
    assert result["ai_evidence"]["sources"][0]["url"] == "https://news/0"
    assert result["ai_evidence"]["citations"][0]["source_ids"] == ["S1"]
