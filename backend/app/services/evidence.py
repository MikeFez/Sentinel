"""Immutable evidence snapshots and validated claim-to-source references."""
import json
from urllib.parse import urlsplit


def safe_url(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme in ("http", "https") and parsed.netloc and not parsed.username else None
    except ValueError:
        return None


def source_catalog(news, stock=None, ratings=None, earnings=None, filings=(), stories=()):
    sources = []

    def add(title, excerpt, url=None, kind="news"):
        sources.append({"id": f"S{len(sources) + 1}", "title": title,
                        "excerpt": str(excerpt or "")[:6000], "url": safe_url(url), "kind": kind})

    for a in news:
        add(a.get("title", "News article"), a.get("summary") or a.get("title"), a.get("url"),
            "user_notes" if a.get("source") == "User" else "news")
    if stock:
        add("Market data at analysis time", json.dumps(stock, default=str), kind="metrics")
    if ratings:
        add("Analyst ratings at analysis time", json.dumps(ratings, default=str), kind="metrics")
    if earnings:
        add("Reported earnings at analysis time", json.dumps(earnings, default=str), kind="metrics")
    for f in filings:
        add(f"{f.form} filed {f.filed_on}", (f.summary or "") +
            ("\nNew risks: " + "; ".join(f.new_risks) if f.new_risks else ""), f.url, "filing")
    for s in stories:
        for a in s.articles:
            add(f"{s.title} — {a.title}", s.summary or s.title, a.url, "story")
    return sources


def validated_evidence(analysis, sources):
    """Resolve only references to supplied source IDs, never model-generated URLs."""
    known = {s["id"] for s in sources}
    sizes = {"summary": len([p for p in analysis.summary.split("\n") if p.strip()]),
             "key_points": len(analysis.key_points), "risks": len(analysis.risks),
             "changes": 1 if analysis.changes else 0}
    citations = []
    for c in analysis.citations:
        if not isinstance(c, dict):
            continue
        section, index = c.get("section"), c.get("index")
        if not isinstance(section, str) or section not in sizes or type(index) is not int or not 0 <= index < sizes[section]:
            continue
        ids = c.get("source_ids")
        if not isinstance(ids, list):
            continue
        ids = list(dict.fromkeys(s for s in ids if isinstance(s, str) and s in known))[:8]
        if ids:
            citations.append({"section": section, "index": index, "source_ids": ids})
    return {"sources": sources, "citations": citations}
