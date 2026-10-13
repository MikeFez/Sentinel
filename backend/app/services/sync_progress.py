"""Which step each running sync is on, for the UI (in memory: a restart fails running syncs anyway).

Steps are keyed by the LLM call's `purpose` where there is one, so `generate()` can advance them
without knowing about syncs. Recording never raises.
"""
from typing import Optional

from . import activity

FETCH = "fetch"
_LABELS = {
    FETCH: "Fetching data",
    "story grouping": "Grouping news into stories",
    "bull case": "Writing the bull case",
    "bear case": "Writing the bear case",
    "analysis": "Writing the analysis",
}

_progress: dict[str, dict] = {}


def begin(company_id: str, public: bool, debate: bool) -> None:
    keys = [FETCH, "story grouping", *(["bull case", "bear case"] if debate else []), "analysis"]
    labels = [("Fetching prices, ratings and news" if public else "Fetching news") if k == FETCH else _LABELS[k] for k in keys]
    _progress[company_id] = {"keys": keys, "steps": labels, "current": 0, "waiting": False}


def step(key: str, waiting: bool = False) -> None:
    """Mark the current company's sync (from activity.context) as on step `key`."""
    p = _progress.get(activity.current_company() or "")
    if p and key in p["keys"]:
        p["current"] = max(p["current"], p["keys"].index(key))
        p["waiting"] = waiting


def end(company_id: str) -> None:
    _progress.pop(company_id, None)


def get(company_id: str) -> Optional[dict]:
    p = _progress.get(company_id)
    return p and {"steps": p["steps"], "current": p["current"], "waiting": p["waiting"]}
