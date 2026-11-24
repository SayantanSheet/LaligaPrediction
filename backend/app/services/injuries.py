"""Injury & availability tracker.

API-Football lists, for each fixture, the players who missed it ("Missing Fixture") or were
doubtful ("Questionable") together with a reason. It does not publish recovery dates, so the
expected return is *estimated* from typical lay-off lengths for the injury type and clearly
labelled as such in the API response.
"""
from __future__ import annotations

import datetime as dt

from .data_store import DataStore

SUSPENSION = ("yellow cards", "red card", "suspended")
OTHER = ("coach's decision", "inactive", "rest", "international duty", "lacking match fitness", "personal reasons")

# typical lay-off in days by keyword (first match wins)
TYPICAL_DAYS = [
    ("cruciate", 240), ("acl", 240), ("achilles", 150), ("surgery", 75), ("broken", 50), ("fracture", 50),
    ("knee", 35), ("hamstring", 24), ("thigh", 21), ("muscle", 18), ("calf", 21), ("groin", 18),
    ("ankle", 21), ("foot", 28), ("toe", 14), ("heel", 21), ("tendon", 35), ("hernia", 35), ("pelvis", 28),
    ("shoulder", 28), ("collarbone", 45), ("wrist", 21), ("hand", 14), ("back", 14), ("abdominal", 21),
    ("head", 10), ("concussion", 12), ("illness", 7), ("health", 10), ("contusion", 7), ("knock", 7),
    ("leg", 21), ("ribs", 21), ("eye", 10), ("nose", 14),
]
SPELL_GAP_DAYS = 18  # absences closer than this belong to the same spell (international breaks)


def category(reason: str | None) -> str:
    r = (reason or "").lower()
    if any(k in r for k in SUSPENSION):
        return "suspension"
    if any(k in r for k in OTHER):
        return "other"
    return "injury"


def typical_days(reason: str | None) -> int:
    r = (reason or "").lower()
    for key, days in TYPICAL_DAYS:
        if key in r:
            return days
    return 21


def _spells(absences: list[dict]) -> list[list[dict]]:
    spells: list[list[dict]] = []
    for a in sorted(absences, key=lambda x: x["date"]):
        d = dt.date.fromisoformat(a["date"])
        if spells and (d - dt.date.fromisoformat(spells[-1][-1]["date"])).days <= SPELL_GAP_DAYS \
                and category(spells[-1][-1]["reason"]) == category(a["reason"]):
            spells[-1].append(a)
        else:
            spells.append([a])
    return spells


def tracker(store: DataStore, team: str | None = None, include_history: bool = False) -> dict:
    """Availability as of the last match date in the data set."""
    ref = dt.date.fromisoformat(store.data_as_of) if store.data_as_of else dt.date.today()
    players_by_id = store.players_by_id
    current, history = [], []
    for row in store.injuries:
        if team and row["team"] != team:
            continue
        spells = _spells(row["absences"])
        if not spells:
            continue
        last = spells[-1]
        start = dt.date.fromisoformat(last[0]["date"])
        end = dt.date.fromisoformat(last[-1]["date"])
        reason = last[-1]["reason"]
        cat = category(reason)
        doubtful = last[-1]["type"] == "Questionable"
        active = (ref - end).days <= 10
        if cat == "suspension":
            est_return = end + dt.timedelta(days=7)
        else:
            est_return = max(start + dt.timedelta(days=typical_days(reason)), ref + dt.timedelta(days=7))
        p = players_by_id.get(row["player_id"], {})
        entry = {
            "player_id": row["player_id"], "player": row["player"], "photo": row.get("photo"),
            "team": row["team"], "team_logo": row.get("team_logo"), "position": p.get("position"),
            "reason": reason, "category": cat,
            "status": ("Suspended" if cat == "suspension" else "Doubtful" if doubtful else
                       "Unavailable" if cat == "other" else "Out") if active else "Available",
            "since": start.isoformat(), "last_missed": end.isoformat(),
            "matches_missed": len(last), "season_matches_missed": len(row["absences"]),
            "days_out": (end - start).days,
            "expected_return": est_return.isoformat() if active else None,
            "expected_return_is_estimate": True,
            "goals": p.get("goals"), "assists": p.get("assists"), "minutes": p.get("minutes"), "rating": p.get("rating"),
            "spells": len(spells),
        }
        (current if active else history).append(entry)

    current.sort(key=lambda e: (e["team"], {"Out": 0, "Suspended": 1, "Doubtful": 2, "Unavailable": 3}[e["status"]], e["player"]))
    by_team: dict[str, int] = {}
    for e in current:
        by_team[e["team"]] = by_team.get(e["team"], 0) + 1
    reasons: dict[str, int] = {}
    for row in store.injuries:
        for a in row["absences"]:
            if category(a["reason"]) == "injury":
                key = (a["reason"] or "Unknown").replace(" Injury", "")
                reasons[key] = reasons.get(key, 0) + 1
    out = {
        "as_of": ref.isoformat(), "season": store.players_season,
        "note": "Expected return dates are estimates based on typical recovery times for the reported injury type.",
        "current": current,
        "summary": {
            "total": len(current),
            "out": sum(1 for e in current if e["status"] == "Out"),
            "doubtful": sum(1 for e in current if e["status"] == "Doubtful"),
            "suspended": sum(1 for e in current if e["status"] == "Suspended"),
            "by_team": sorted(({"team": t, "count": c, "logo": store.team_meta(t).get("logo")} for t, c in by_team.items()), key=lambda r: -r["count"]),
            "top_reasons": sorted(({"reason": r, "count": c} for r, c in reasons.items()), key=lambda r: -r["count"])[:10],
        },
    }
    if include_history:
        out["history"] = sorted(history, key=lambda e: e["last_missed"], reverse=True)
    return out


def team_impact(store: DataStore, team: str, unavailable: list[dict] | None = None) -> dict:
    """Translate unavailable players into multipliers on the team's expected goals.

    attack: weight = 0.6 * share of team goal contributions + 0.4 * share of team minutes (outfield),
            capped so the team keeps at least 85% of its expected goals.
    defence: missing goalkeepers/defenders raise the opponent's expected goals by up to 10%.
    """
    if unavailable is None:
        unavailable = [e for e in tracker(store, team)["current"] if e["status"] in ("Out", "Suspended")]
    squad = [p for p in store.players if p["team"] == team]
    total_ga = sum(p["goals"] + p["assists"] for p in squad) or 1
    total_min = sum(p["minutes"] for p in squad) or 1
    attack_loss, defence_loss, details = 0.0, 0.0, []
    for e in unavailable:
        p = store.players_by_id.get(e["player_id"])
        if not p or p["team"] != team:
            continue
        ga_share = (p["goals"] + p["assists"]) / total_ga
        min_share = p["minutes"] / total_min
        a = 0.6 * ga_share + 0.4 * min_share * (0 if p["position"] in ("Goalkeeper", "Defender") else 1)
        d = min_share * (1.5 if p["position"] == "Goalkeeper" else 1.0 if p["position"] == "Defender" else 0.3)
        attack_loss += 0.35 * a
        defence_loss += 0.25 * d
        details.append({"player": p["name"], "player_id": p["id"], "position": p["position"], "status": e["status"],
                        "goals": p["goals"], "assists": p["assists"], "impact": round(0.35 * a + 0.25 * d, 4)})
    attack_mult = 1 - min(0.15, attack_loss)
    opp_mult = 1 + min(0.10, defence_loss)
    return {"attack_multiplier": round(attack_mult, 4), "opponent_attack_multiplier": round(opp_mult, 4),
            "players": sorted(details, key=lambda d: -d["impact"])}
