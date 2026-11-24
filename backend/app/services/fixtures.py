"""Live scores and upcoming fixtures from API-Football (cached, quota-aware).

Free-plan constraints (verified against the API): date queries are limited to yesterday/today/
tomorrow, `live=all` is allowed, and season queries are limited to 2022-2024. Requests are cached
in SQLite and capped by DAILY_REQUEST_BUDGET; when the budget is exhausted the last cached response
is served and flagged as stale.
"""
from __future__ import annotations

import datetime as dt

from .. import config
from . import football_api
from .data_store import canonical_team

LIVE_STATUSES = {"1H", "HT", "2H", "ET", "BT", "P", "SUSP", "INT", "LIVE"}
FINISHED = {"FT", "AET", "PEN"}
UPCOMING = {"NS", "TBD", "PST"}


def _fmt(f: dict) -> dict:
    st = f["fixture"]["status"]
    return {
        "id": f["fixture"]["id"],
        "kickoff": f["fixture"]["date"],
        "timestamp": f["fixture"]["timestamp"],
        "status": st["short"], "status_long": st["long"], "elapsed": st.get("elapsed"),
        "round": (f["league"].get("round") or "").replace("Regular Season - ", "Matchday "),
        "season": f["league"].get("season"),
        "venue": (f["fixture"].get("venue") or {}).get("name"),
        "home_team": canonical_team(f["teams"]["home"]["name"]), "home_logo": f["teams"]["home"]["logo"],
        "away_team": canonical_team(f["teams"]["away"]["name"]), "away_logo": f["teams"]["away"]["logo"],
        "home_score": f["goals"]["home"], "away_score": f["goals"]["away"],
        "halftime": f.get("score", {}).get("halftime"),
        "is_live": st["short"] in LIVE_STATUSES,
    }


def _day(offset: int) -> str:
    return (dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=offset)).isoformat()


def _by_date(offset: int) -> tuple[list[dict], dict]:
    ttl = config.TTL["today"] if offset == 0 else 6 * 3600 if offset > 0 else config.TTL["finished"]
    res = football_api.get("fixtures", {"date": _day(offset)}, ttl)
    if res is None:
        return [], {"source": "unavailable", "fetched_at": None}
    rows = [_fmt(f) for f in res.data or [] if f["league"]["id"] == config.LEAGUE_ID]
    return rows, {"source": res.source, "fetched_at": res.fetched_at.isoformat() + "Z"}


def live() -> dict:
    today, meta = _by_date(0)
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    # Only spend live requests while a LaLiga match can actually be in progress.
    window = any(f["timestamp"] - 900 <= now <= f["timestamp"] + 3 * 3600 for f in today if f["status"] not in FINISHED)
    matches = [f for f in today if f["is_live"]]
    if window:
        res = football_api.get("fixtures", {"live": "all"}, config.TTL["live"])
        if res is not None:
            live_rows = [_fmt(f) for f in res.data or [] if f["league"]["id"] == config.LEAGUE_ID]
            matches = live_rows
            meta = {"source": res.source, "fetched_at": res.fetched_at.isoformat() + "Z"}
    return {"matches": matches, "today": today, "polling": window, **meta}


def upcoming() -> dict:
    today, meta_t = _by_date(0)
    tomorrow, meta_n = _by_date(1)
    rows = [f for f in today + tomorrow if f["status"] in UPCOMING]
    rows.sort(key=lambda f: f["timestamp"])
    return {"matches": rows, "source": meta_n["source"], "fetched_at": meta_n["fetched_at"],
            "window": [_day(0), _day(1)],
            "note": "The free API-Football plan only exposes fixtures from yesterday to tomorrow."}


def recent_results() -> dict:
    yesterday, _ = _by_date(-1)
    today, meta = _by_date(0)
    rows = [f for f in yesterday + today if f["status"] in FINISHED]
    rows.sort(key=lambda f: -f["timestamp"])
    return {"matches": rows, **meta}
