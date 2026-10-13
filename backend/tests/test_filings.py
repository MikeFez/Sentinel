import asyncio

from app.services.filings import html_to_text, new_paragraphs, risk_factors, summarize

P = "Our business depends on launch cadence and customer demand, which may vary significantly from quarter to quarter " * 3


def test_html_to_text_keeps_paragraphs():
    text = html_to_text("<html><style>x{}</style><p>One &amp; two</p><div>Three<br>Four</div></html>")
    assert text.split("\n") == ["One & two", "Three", "Four"]


def test_risk_factors_skips_the_table_of_contents():
    body = "Item 1A. Risk Factors 12\nItem 1B. Unresolved 30\n" + "Item 1A. Risk Factors\n" + P * 3 + "\nItem 1B. Unresolved Staff Comments"
    assert risk_factors(body).startswith("Our business depends")


def test_new_paragraphs_ignores_reworded_ones():
    old = P + "\n" + "Competition from larger launch providers could reduce our pricing power and margins over time " * 3
    reworded = P.replace("significantly", "materially")
    brand_new = "New tariffs on imported components could raise our costs and delay deliveries to customers " * 3
    assert new_paragraphs(old, reworded + "\n" + brand_new) == [brand_new]


class Scripted:
    def __init__(self, replies):
        self.replies, self.prompts, self.last_error = list(replies), [], None

    async def generate(self, prompt, timeout=60, json_mode=False, purpose="other"):
        self.prompts.append(prompt)
        return self.replies.pop(0)


def test_10k_summary_includes_new_risks():
    brand_new = "New tariffs on imported components could raise our costs and delay deliveries to customers " * 3
    filing = {"form": "10-K", "filed_on": "2026-03-01", "text": "annual report text " * 50,
              "risk_text": P + "\n" + brand_new, "previous_risk_text": P}
    llm = Scripted(["Revenue grew 40%.", '{"risks": ["Tariffs on components"]}'])
    summary, risks, error = asyncio.run(summarize(llm, "Acme", filing))
    assert (summary, risks, error) == ("Revenue grew 40%.", ["Tariffs on components"], None)
    assert "New tariffs" in llm.prompts[1] and "launch cadence" not in llm.prompts[1]


def test_8k_summary_and_llm_failure():
    f = {"form": "8-K", "filed_on": "2026-10-01", "items": "5.02", "text": "The CFO resigned."}
    llm = Scripted(["The CFO resigned."])
    assert asyncio.run(summarize(llm, "Acme", f))[0] == "The CFO resigned." and "items 5.02" in llm.prompts[0]
    down = Scripted([None]); down.last_error = "timeout"
    assert asyncio.run(summarize(down, "Acme", f)) == (None, None, "timeout")


def test_only_recent_filings_are_ever_fetched(db, monkeypatch):
    """Later checks must not walk back through a company's whole filing history."""
    from datetime import date, timedelta

    from app.models import Filing
    from app.services import filings
    from tests import factories as f

    c = f.company(db, "Acme", "ACME")
    recent, old = (date.today() - timedelta(days=d) for d in (10, 400))
    listing = [
        {"form": "8-K", "accession": "new-1", "filed_on": recent.isoformat(), "items": None, "url": "u1"},
        {"form": "10-Q", "accession": "old-1", "filed_on": old.isoformat(), "items": None, "url": "u2"},
    ]
    monkeypatch.setattr(filings, "cik_for", lambda t: "0000000001")
    monkeypatch.setattr(filings, "recent_filings", lambda cik: listing)
    monkeypatch.setattr(filings, "_get", lambda client, url, name: type("R", (), {"text": "<p>text</p>"})())
    db.add(Filing(company_id=c.id, accession="known", form="8-K", filed_on=recent.isoformat(), url="u0"))
    db.commit()
    assert [x["accession"] for x in filings.fetch_new(db, c)] == ["new-1"]


def test_routine_marker_is_stripped_and_flagged():
    from app.services.filings import split_routine

    assert split_routine("8-K", "Routine: the company filed its investor slides.") == (True, "The company filed its investor slides.")
    assert split_routine("8-K", "**Routine** — vote results.") == (True, "Vote results.")
    assert split_routine("8-K", "The CFO resigned; routine succession follows.") == (False, "The CFO resigned; routine succession follows.")
    assert split_routine("10-K", "Routine: x") == (False, "Routine: x")  # only 8-Ks
    # Results are never routine, even when the model says so
    assert split_routine("8-K", "Routine: Q2 results press release.", "2.02,9.01") == (False, "Q2 results press release.")
