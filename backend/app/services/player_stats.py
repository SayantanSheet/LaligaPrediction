"""Player analytics: listing, leaders, profiles, per-90 percentiles and comparisons."""
from __future__ import annotations

import numpy as np

from .data_store import DataStore

MIN_MINUTES_FOR_PERCENTILE = 450

# metric key -> (label, per90?, higher_is_better)
METRICS = {
    "goals": ("Goals", True, True),
    "assists": ("Assists", True, True),
    "shots": ("Shots", True, True),
    "shots_on": ("Shots on target", True, True),
    "key_passes": ("Key passes", True, True),
    "passes": ("Passes", True, True),
    "pass_accuracy": ("Pass accuracy", False, True),
    "dribbles_won": ("Successful dribbles", True, True),
    "tackles": ("Tackles", True, True),
    "interceptions": ("Interceptions", True, True),
    "duels_won": ("Duels won", True, True),
    "fouls_drawn": ("Fouls drawn", True, True),
    "rating": ("Average rating", False, True),
}
RADAR_KEYS = ["goals", "assists", "shots_on", "key_passes", "dribbles_won", "tackles", "interceptions", "duels_won", "rating"]


def per90(p: dict, key: str) -> float | None:
    v = p.get(key)
    if v is None or (key == "pass_accuracy" and not v):  # API leaves pass accuracy empty for most players
        return None
    label, is_per90, _ = METRICS.get(key, (key, False, True))
    if not is_per90:
        return float(v)
    return round(90.0 * v / p["minutes"], 2) if p.get("minutes") else 0.0


def _position_pool(store: DataStore, position: str) -> list[dict]:
    pool = [p for p in store.players if p["position"] == position and p["minutes"] >= MIN_MINUTES_FOR_PERCENTILE]
    return pool or [p for p in store.players if p["minutes"] >= MIN_MINUTES_FOR_PERCENTILE]


def percentiles(store: DataStore, p: dict) -> dict:
    pool = _position_pool(store, p["position"])
    out = {}
    for key in METRICS:
        mine = per90(p, key)
        vals = np.array([v for v in (per90(q, key) for q in pool) if v is not None])
        if mine is None or len(vals) == 0:
            out[key] = None
            continue
        out[key] = round(float((vals < mine).mean() * 100 + (vals == mine).mean() * 50), 1)
    return out


def summary(p: dict) -> dict:
    keys = ("id", "name", "photo", "team", "team_logo", "position", "age", "nationality", "appearances",
            "minutes", "goals", "assists", "rating", "shots", "key_passes", "yellow", "red")
    s = {k: p.get(k) for k in keys}
    s["ga_per90"] = round(90 * (p["goals"] + p["assists"]) / p["minutes"], 2) if p.get("minutes") else 0
    return s


def list_players(store: DataStore, team: str | None = None, position: str | None = None, q: str | None = None,
                 sort: str = "rating", min_minutes: int = 0, limit: int = 500) -> list[dict]:
    rows = store.players
    if team:
        rows = [p for p in rows if p["team"] == team]
    if position:
        rows = [p for p in rows if p["position"].lower() == position.lower()]
    if q:
        ql = q.lower()
        rows = [p for p in rows if ql in p["name"].lower() or ql in (p.get("lastname") or "").lower()]
    rows = [p for p in rows if p["minutes"] >= min_minutes]
    out = [summary(p) for p in rows]
    out.sort(key=lambda r: (r.get(sort) is None, -(r.get(sort) or 0)))
    return out[:limit]


def leaders(store: DataStore, limit: int = 10) -> dict:
    def top(key, min_minutes=0, per_90=False):
        pool = [p for p in store.players if p["minutes"] >= min_minutes and p.get(key) is not None]
        val = (lambda p: per90(p, key)) if per_90 else (lambda p: p[key])
        pool.sort(key=lambda p: -val(p))
        return [summary(p) | {"value": val(p)} for p in pool[:limit]]

    for p in store.players:
        p["ga"] = p["goals"] + p["assists"]
    return {
        "goals": top("goals"), "assists": top("assists"), "goal_contributions": top("ga"),
        "rating": top("rating", 900), "key_passes": top("key_passes"), "dribbles": top("dribbles_won"),
        "tackles": top("tackles"), "goals_per90": top("goals", 900, per_90=True),
        "season": store.players_season,
    }


def profile(store: DataStore, player_id: int) -> dict | None:
    p = store.players_by_id.get(player_id)
    if not p:
        return None
    team_players = [q for q in store.players if q["team"] == p["team"]]
    team_goals = sum(q["goals"] for q in team_players) or 1
    return {
        **p,
        "per90": {k: per90(p, k) for k in METRICS},
        "percentiles": percentiles(store, p),
        "percentile_pool": f"{p['position']}s with {MIN_MINUTES_FOR_PERCENTILE}+ minutes",
        "share_of_team_goals": round(p["goals"] / team_goals, 3),
        "shot_accuracy": round(p["shots_on"] / p["shots"], 3) if p.get("shots") else None,
        "conversion_rate": round(p["goals"] / p["shots"], 3) if p.get("shots") else None,
        "dribble_success": round(p["dribbles_won"] / p["dribbles"], 3) if p.get("dribbles") else None,
        "duel_success": round(p["duels_won"] / p["duels"], 3) if p.get("duels") else None,
        "minutes_per_goal": round(p["minutes"] / p["goals"]) if p.get("goals") else None,
        "recent": p.get("recent", []),
        "season": store.players_season,
    }


def compare(store: DataStore, a: int, b: int) -> dict | None:
    pa, pb = profile(store, a), profile(store, b)
    if not pa or not pb:
        return None
    rows = []
    for key, (label, is_per90, higher) in METRICS.items():
        va, vb = pa["per90"][key], pb["per90"][key]
        better = None
        if va is not None and vb is not None and va != vb:
            better = "a" if (va > vb) == higher else "b"
        rows.append({"key": key, "label": label + (" / 90" if is_per90 else ""), "a": va, "b": vb,
                     "a_total": pa.get(key), "b_total": pb.get(key), "better": better,
                     "a_pct": pa["percentiles"].get(key), "b_pct": pb["percentiles"].get(key)})
    radar = [{"metric": METRICS[k][0], "a": pa["percentiles"].get(k) or 0, "b": pb["percentiles"].get(k) or 0} for k in RADAR_KEYS]
    wins_a = sum(1 for r in rows if r["better"] == "a")
    wins_b = sum(1 for r in rows if r["better"] == "b")
    return {"a": pa, "b": pb, "rows": rows, "radar": radar, "edge": {"a": wins_a, "b": wins_b}}
