"""SEC filings for tracked public companies: find new 8-K / 10-Q / 10-K filings, summarize them,
and for 10-Ks find risk factors that are new since the previous 10-K."""
import html
import json
import logging
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Company, Filing
from . import activity
from .llm_service import LLMService

logger = logging.getLogger(__name__)

FORMS = ("8-K", "10-Q", "10-K")
LOOKBACK_DAYS = 120  # only filings this recent are ever summarized (checks run daily, so nothing new is missed)
MAX_NEW_PER_CHECK = 4
DOC_CHARS = 24_000  # filing text sent to the LLM
NEW_RISK_CHARS = 12_000

_cik_cache: dict = {"at": 0.0, "map": {}}


def _client() -> httpx.Client:
    return httpx.Client(timeout=30, headers={"User-Agent": settings.sec_user_agent}, follow_redirects=True)


def _get(client: httpx.Client, url: str, name: str) -> httpx.Response:
    with activity.track("sec", name) as t:
        r = client.get(url)
        if r.status_code >= 400:
            t.fail(f"HTTP {r.status_code}")
        return r


def _get_json(client: httpx.Client, url: str):
    r = _get(client, url, "tickers" if "company_tickers" in url else "submissions")
    if r.status_code == 403:
        raise RuntimeError("SEC rejected the request; set SEC_USER_AGENT to 'YourName your@email' (SEC's fair-access policy)")
    r.raise_for_status()
    return r.json()


def cik_for(ticker: str) -> Optional[str]:
    """SEC's ticker → CIK map, cached for a day."""
    if time.time() - _cik_cache["at"] > 86400:
        with _client() as c:
            data = _get_json(c, "https://www.sec.gov/files/company_tickers.json")
        _cik_cache.update(at=time.time(), map={v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()})
    return _cik_cache["map"].get(ticker.upper())


def recent_filings(cik: str) -> list[dict]:
    """8-K / 10-Q / 10-K filings from the submissions API, newest first."""
    with _client() as c:
        recent = _get_json(c, f"https://data.sec.gov/submissions/CIK{cik}.json")["filings"]["recent"]
    out = []
    for i, form in enumerate(recent["form"]):
        if form not in FORMS:
            continue
        acc = recent["accessionNumber"][i]
        out.append({
            "form": form,
            "accession": acc,
            "filed_on": recent["filingDate"][i],
            "items": (recent.get("items") or [""] * len(recent["form"]))[i] or None,
            "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{recent['primaryDocument'][i]}",
        })
    return out


_BLOCK = re.compile(r"<\s*(/?)(p|div|br|li|tr|h\d|table)\b[^>]*>", re.I)


def html_to_text(raw: str) -> str:
    """Plain text with one paragraph per line."""
    raw = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.S | re.I)
    raw = _BLOCK.sub("\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    lines = (re.sub(r"[ \t ]+", " ", line).strip() for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def section(text: str, start: str, end: str) -> Optional[str]:
    """The longest span between a `start` heading and the next `end` heading (skips the table of contents)."""
    best = None
    for m in re.finditer(start, text, re.I):
        stop = re.search(end, text[m.end():], re.I)
        if not stop:
            continue
        body = text[m.end(): m.end() + stop.start()]
        if best is None or len(body) > len(best):
            best = body
    return best.strip() if best and len(best) > 500 else None


def risk_factors(text: str) -> Optional[str]:
    return section(text, r"item\s*1a\.?\s*risk\s*factors", r"item\s*1b\.?|item\s*2\.?\s*properties")


def mdna(text: str, form: str) -> Optional[str]:
    if form == "10-K":
        return section(text, r"item\s*7\.?\s*management", r"item\s*7a\.?|item\s*8\.?")
    return section(text, r"item\s*2\.?\s*management", r"item\s*3\.?|item\s*4\.?")


def _shingles(paragraph: str) -> set:
    words = re.findall(r"[a-z0-9]+", paragraph.lower())
    return {" ".join(words[i:i + 5]) for i in range(max(1, len(words) - 4))}


def new_paragraphs(old: str, new: str, min_len: int = 200, threshold: float = 0.5) -> list[str]:
    """Paragraphs of `new` with no close match (5-word shingle overlap) in `old`."""
    old_sets = [_shingles(p) for p in old.split("\n") if len(p) >= min_len]
    added = []
    for p in new.split("\n"):
        if len(p) < min_len:
            continue
        s = _shingles(p)
        if not any(len(s & o) / len(s | o) >= threshold for o in old_sets if o):
            added.append(p)
    return added


def fetch_new(db: Session, company: Company, limit_days: Optional[int] = None) -> list[dict]:
    """New filings for one company, with their text (blocking: SEC requests). Not yet saved."""
    cik = cik_for(company.ticker)
    if not cik:
        return []
    known = {a for (a,) in db.query(Filing.accession).filter(Filing.company_id == company.id)}
    cutoff = (date.today() - timedelta(days=limit_days or LOOKBACK_DAYS)).isoformat()
    filings = recent_filings(cik)
    new = [f for f in filings if f["accession"] not in known and f["filed_on"] >= cutoff][:MAX_NEW_PER_CHECK]
    with _client() as c:
        for f in new:
            time.sleep(0.2)  # well under SEC's 10 requests a second
            f["text"] = html_to_text(_get(c, f["url"], "filing document").text)
            if f["form"] == "10-K":
                f["risk_text"] = risk_factors(f["text"])
                previous = next((p for p in filings if p["form"] == "10-K" and p["filed_on"] < f["filed_on"]), None)
                stored = (
                    db.query(Filing).filter(Filing.company_id == company.id, Filing.form == "10-K",
                                            Filing.filed_on < f["filed_on"], Filing.risk_text.isnot(None))
                    .order_by(Filing.filed_on.desc()).first()
                )
                if stored:
                    f["previous_risk_text"] = stored.risk_text
                elif previous:
                    f["previous_risk_text"] = risk_factors(html_to_text(_get(c, previous["url"], "filing document").text))
    return new


SUMMARY_PROMPTS = {
    "8-K": "Summarize what this 8-K current report discloses in 1-3 sentences for an investor. Lead with the event "
           "(results, leadership change, agreement, financing, etc.). If it's routine, say so briefly.",
    "10-Q": "Summarize this quarterly report in 2-4 sentences for an investor: revenue and profit versus last year, "
            "guidance, and anything notable that changed.",
    "10-K": "Summarize this annual report in 2-4 sentences for an investor: the year's results, strategy, and "
            "anything notable that changed.",
}


async def summarize(llm: LLMService, company_name: str, f: dict) -> tuple[Optional[str], Optional[list[str]], Optional[str]]:
    """(summary, new_risks, error) for a fetched filing."""
    body = (mdna(f["text"], f["form"]) if f["form"] != "8-K" else None) or f["text"]
    prompt = (
        f"{company_name} filed a {f['form']} on {f['filed_on']}"
        + (f" (items {f['items']})" if f.get("items") else "")
        + f".\n\n{SUMMARY_PROMPTS[f['form']]}\nPlain prose, no preamble.\n\n--- Filing text ---\n{body[:DOC_CHARS]}"
    )
    summary = await llm.generate(prompt, timeout=180, purpose="filing summary")
    if summary is None:
        return None, None, llm.last_error
    new_risks = None
    if f["form"] == "10-K" and f.get("risk_text") and f.get("previous_risk_text"):
        added = new_paragraphs(f["previous_risk_text"], f["risk_text"])
        if added:
            reply = await llm.generate(
                f"These risk-factor paragraphs are new in {company_name}'s latest 10-K compared with the previous one.\n"
                "List the new or expanded risks as short phrases (at most 6). Respond with one JSON object: "
                '{"risks": ["..."]}\n\n' + "\n\n".join(added)[:NEW_RISK_CHARS],
                timeout=180, json_mode=True, purpose="new risk factors",
            )
            new_risks = _risk_list(reply) if reply else None
        else:
            new_risks = []
    return summary.strip(), new_risks, None


def _risk_list(reply: str) -> Optional[list[str]]:
    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.S)
    start, end = reply.find("{"), reply.rfind("}")
    try:
        risks = json.loads(reply[start:end + 1]).get("risks")
    except (ValueError, AttributeError):
        return None
    return [str(r).strip() for r in risks or [] if str(r).strip()][:6]


def save(db: Session, company_id: str, f: dict, summary, new_risks, error) -> Filing:
    filing = Filing(
        company_id=company_id, accession=f["accession"], form=f["form"], filed_on=f["filed_on"],
        items=f.get("items"), url=f["url"], summary=summary, new_risks=new_risks,
        risk_text=f.get("risk_text"), error=error,
    )
    db.add(filing)
    db.commit()
    return filing


_last_check: dict[str, datetime] = {}


async def check_filings(session_factory, llm: LLMService, hours: float = 24) -> int:
    """Find and summarize new filings for every public company (each checked at most every `hours`)."""
    import asyncio

    now = datetime.now(timezone.utc)
    db = session_factory()
    saved = 0
    try:
        companies = db.query(Company).filter(Company.status == "public", Company.ticker.isnot(None)).all()
        for company in companies:
            if company.id in _last_check and now - _last_check[company.id] < timedelta(hours=hours):
                continue
            _last_check[company.id] = now
            try:
                with activity.context(company_id=company.id):
                    fetched = await asyncio.to_thread(_fetch_in_thread, session_factory, company.id)
            except Exception as e:
                logger.warning(f"SEC filings check failed for {company.name}: {e}")
                continue
            for f in fetched:
                with activity.context(company_id=company.id):
                    summary, new_risks, error = await summarize(llm, company.name, f)
                if error:  # LLM unavailable: leave it unsaved so the next check retries it
                    logger.warning(f"Could not summarize {company.name} {f['form']} {f['filed_on']}: {error}")
                    _last_check.pop(company.id, None)
                    break
                save(db, company.id, f, summary, new_risks, None)
                saved += 1
    finally:
        db.close()
    return saved


def _fetch_in_thread(session_factory, company_id: str) -> list[dict]:
    db = session_factory()
    try:
        return fetch_new(db, db.get(Company, company_id))
    finally:
        db.close()
