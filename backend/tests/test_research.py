from app.routers import analyze as analyze_router
from app.services import discover_service
from app.services.llm_service import Analysis


class FakeLLM:
    def __init__(self, *a, **k):
        self.last_error = None

    async def analyze_company(self, **kwargs):
        return Analysis(summary="Looks fine.", sentiment="bearish"), "prompt"


def test_analysis_is_saved_listed_reopened_and_deleted(client, monkeypatch):
    monkeypatch.setattr(analyze_router, "LLMService", FakeLLM)
    result = client.post("/api/analyze", json={"company_name": "Acme", "notes": "a thesis"}).json()
    assert result["sentiment"] == "bearish" and result["id"]

    [row] = client.get("/api/research?kind=analysis").json()
    assert (row["id"], row["title"], row["sentiment"], row["summary"]) == (result["id"], "Acme", "bearish", "Looks fine.")

    saved = client.get(f"/api/research/{row['id']}").json()
    assert saved["data"]["request"]["notes"] == "a thesis" and saved["data"]["result"]["summary"] == "Looks fine."

    assert client.delete(f"/api/research/{row['id']}").status_code == 204
    assert client.get("/api/research").json() == []


def test_discovery_is_saved_and_reloads_after_a_restart(client):
    session = discover_service.create_session("Water desalination")
    session["status"] = "validating"  # still running when the server stopped
    session["companies"] = [{"ticker": "AAA", "name": "A", "status": "analyzing", "sentiment": None}]
    discover_service._persist(session)
    discover_service._sessions.clear()  # what a restart does

    reloaded = client.get(f"/api/discover/{session['session_id']}").json()
    assert reloaded["theme"] == "Water desalination"
    assert reloaded["status"] == "failed" and "restart" in reloaded["error"]
    assert reloaded["companies"][0]["status"] == "pending"
    [row] = client.get("/api/research?kind=discovery").json()
    assert (row["title"], row["companies"]) == ("Water desalination", 1)
