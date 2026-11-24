"""Build the bundled offline snapshot from API-Football.

Usage (from backend/):  python -m scripts.build_snapshot [--fetch] [--player-logs N]

* Raw responses are stored in data/raw/ and never re-requested, so the script is resumable
  across days when the free-plan quota (100 req/day) runs out.
* Processing turns raw responses into compact JSON in data/snapshot/, which the API serves
  whenever live data is unavailable.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import time

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.services.data_store import canonical_team  # noqa: E402

RAW = config.RAW_DIR
SNAP = config.SNAPSHOT_DIR
HARD_STOP = 96  # never let the account go above this many requests in a day


MIN_INTERVAL = 7.0  # free plan: 10 requests/minute
_last_call = 0.0
_used_counter: int | None = None


def _throttle() -> None:
    global _last_call
    wait = MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def api_used_today() -> int:
    """Read the account's request counter once, then count locally (status calls are rate-limited too)."""
    global _used_counter
    if _used_counter is None:
        _throttle()
        r = httpx.get(f"{config.API_FOOTBALL_BASE}/status",
                      headers={"x-apisports-key": config.API_FOOTBALL_KEY}, timeout=20)
        resp = r.json().get("response")
        if not isinstance(resp, dict):
            raise SystemExit(f"Could not read API status: {r.json().get('errors')}")
        _used_counter = int(resp["requests"]["current"])
    return _used_counter


def fetch(name: str, endpoint: str, params: dict) -> list | None:
    path = RAW / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    if api_used_today() >= HARD_STOP:
        print(f"  ! quota nearly exhausted, skipping {name}")
        return None
    global _used_counter
    _throttle()
    _used_counter = api_used_today() + 1
    for attempt in range(3):
        try:
            r = httpx.get(f"{config.API_FOOTBALL_BASE}/{endpoint}", params=params,
                          headers={"x-apisports-key": config.API_FOOTBALL_KEY}, timeout=60)
            break
        except httpx.TransportError as exc:
            print(f"  ! network error on {name} ({exc}); retrying")
            time.sleep(10 * (attempt + 1))
    else:
        return None
    body = r.json()
    if body.get("errors"):
        print(f"  ! {name}: {body['errors']}")
        return None
    data = body.get("response", [])
    if endpoint == "players":
        data = {"paging": body["paging"], "response": data}
    path.write_text(json.dumps(data))
    print(f"  + {name}")
    return data


def fetch_all() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    season = max(config.TRAINING_SEASONS)
    for s in config.TRAINING_SEASONS:
        fetch(f"fixtures_league140_season{s}", "fixtures", {"league": 140, "season": s})
    fetch(f"teams_season{season}", "teams", {"league": 140, "season": season})
    fetch(f"standings_season{season}", "standings", {"league": 140, "season": season})
    fetch(f"topscorers_season{season}", "players/topscorers", {"league": 140, "season": season})
    fetch(f"topassists_season{season}", "players/topassists", {"league": 140, "season": season})
    fetch(f"injuries_season{season}", "injuries", {"league": 140, "season": season})
    # The free plan caps `page` at 3, so league-wide paging cannot cover ~600 players.
    # Query per team instead (2 pages x 20 players covers every regular squad member).
    teams = json.loads((RAW / f"teams_season{season}.json").read_text())
    for t in teams:
        tid = t["team"]["id"]
        for page in (1, 2):
            data = fetch(f"players_team{tid}_season{season}_p{page}", "players",
                         {"team": tid, "season": season, "page": page})
            if data is None or data["paging"]["total"] <= page:
                break


def fetch_player_logs(n_rounds: int) -> None:
    """Per-fixture player ratings for the last n rounds (10 requests per round)."""
    season = max(config.TRAINING_SEASONS)
    fixtures = json.loads((RAW / f"fixtures_league140_season{season}.json").read_text())
    fixtures.sort(key=lambda f: f["fixture"]["timestamp"])
    for f in fixtures[-10 * n_rounds:][::-1]:
        fid = f["fixture"]["id"]
        if fetch(f"fixture_players_{fid}", "fixtures/players", {"fixture": fid}) is None:
            break


# --------------------------------------------------------------------------- processing

def _f(v, default=0):
    return default if v is None else v


def process() -> None:
    SNAP.mkdir(parents=True, exist_ok=True)
    season = max(config.TRAINING_SEASONS)

    # ---- matches + team metadata
    matches, teams = [], {}
    for s in config.TRAINING_SEASONS:
        path = RAW / f"fixtures_league140_season{s}.json"
        if not path.exists():
            continue
        for f in json.loads(path.read_text()):
            h, a = f["teams"]["home"], f["teams"]["away"]
            for t in (h, a):
                teams[canonical_team(t["name"])] = {"id": t["id"], "name": canonical_team(t["name"]), "logo": t["logo"]}
            if f["fixture"]["status"]["short"] not in ("FT", "AET", "PEN"):
                continue
            ht = f["score"]["halftime"]
            matches.append({
                "id": f["fixture"]["id"],
                "date": f["fixture"]["date"][:10],
                "season": f["league"]["season"],
                "round": f["league"]["round"].replace("Regular Season - ", ""),
                "homeTeam": canonical_team(h["name"]),
                "awayTeam": canonical_team(a["name"]),
                "homeScore": f["goals"]["home"],
                "awayScore": f["goals"]["away"],
                "homeHT": ht["home"],
                "awayHT": ht["away"],
                "venue": f["fixture"]["venue"]["name"],
                "referee": f["fixture"]["referee"],
            })
    matches.sort(key=lambda m: (m["date"], m["id"]))
    (SNAP / "matches.json").write_text(json.dumps(matches))
    print(f"matches: {len(matches)}")

    team_raw = RAW / f"teams_season{season}.json"
    if team_raw.exists():
        for t in json.loads(team_raw.read_text()):
            name = canonical_team(t["team"]["name"])
            teams.setdefault(name, {"id": t["team"]["id"], "name": name, "logo": t["team"]["logo"]})
            teams[name].update({
                "code": t["team"].get("code"),
                "founded": t["team"].get("founded"),
                "venue": t["venue"].get("name"),
                "city": t["venue"].get("city"),
                "capacity": t["venue"].get("capacity"),
            })
    (SNAP / "teams.json").write_text(json.dumps(sorted(teams.values(), key=lambda t: t["name"])))
    print(f"teams: {len(teams)}")

    # ---- standings
    st_raw = RAW / f"standings_season{season}.json"
    if st_raw.exists():
        table = json.loads(st_raw.read_text())[0]["league"]["standings"][0]
        standings = [{
            "rank": r["rank"], "team": canonical_team(r["team"]["name"]), "logo": r["team"]["logo"],
            "points": r["points"], "goal_diff": r["goalsDiff"], "form": r.get("form") or "",
            "played": r["all"]["played"], "won": r["all"]["win"], "drawn": r["all"]["draw"], "lost": r["all"]["lose"],
            "goals_for": r["all"]["goals"]["for"], "goals_against": r["all"]["goals"]["against"],
            "description": r.get("description"),
        } for r in table]
        (SNAP / "standings.json").write_text(json.dumps({"season": season, "table": standings}))

    # ---- players (season aggregates)
    players = {}
    for path in sorted(RAW.glob(f"players_*season{season}_p*.json")):
        for item in json.loads(path.read_text())["response"]:
            pl = item["player"]
            st = next((s for s in item["statistics"] if s["league"]["id"] == 140), None)
            if st is None or pl["id"] in players:
                continue
            games = st["games"]
            minutes = _f(games.get("minutes"))
            if minutes < 1:
                continue
            players[pl["id"]] = {
                "id": pl["id"], "name": pl["name"],
                "firstname": pl.get("firstname"), "lastname": pl.get("lastname"),
                "age": pl.get("age"), "nationality": pl.get("nationality"),
                "height": pl.get("height"), "photo": pl.get("photo"),
                "team": canonical_team(st["team"]["name"]), "team_logo": st["team"]["logo"],
                "position": games.get("position") or "Unknown",
                "appearances": _f(games.get("appearences")), "lineups": _f(games.get("lineups")),
                "minutes": minutes,
                "rating": round(float(games["rating"]), 2) if games.get("rating") else None,
                "captain": bool(games.get("captain")),
                "goals": _f(st["goals"].get("total")), "assists": _f(st["goals"].get("assists")),
                "conceded": _f(st["goals"].get("conceded")), "saves": _f(st["goals"].get("saves")),
                "shots": _f(st["shots"].get("total")), "shots_on": _f(st["shots"].get("on")),
                "passes": _f(st["passes"].get("total")), "key_passes": _f(st["passes"].get("key")),
                "pass_accuracy": _f(st["passes"].get("accuracy")),
                "tackles": _f(st["tackles"].get("total")), "blocks": _f(st["tackles"].get("blocks")),
                "interceptions": _f(st["tackles"].get("interceptions")),
                "duels": _f(st["duels"].get("total")), "duels_won": _f(st["duels"].get("won")),
                "dribbles": _f(st["dribbles"].get("attempts")), "dribbles_won": _f(st["dribbles"].get("success")),
                "fouls_drawn": _f(st["fouls"].get("drawn")), "fouls_committed": _f(st["fouls"].get("committed")),
                "yellow": _f(st["cards"].get("yellow")), "red": _f(st["cards"].get("red")),
                "pen_scored": _f(st["penalty"].get("scored")), "pen_missed": _f(st["penalty"].get("missed")),
            }

    # ---- per-match player logs
    logs = defaultdict(list)
    fixtures_by_id = {m["id"]: m for m in matches}
    for path in RAW.glob("fixture_players_*.json"):
        fid = int(path.stem.rsplit("_", 1)[1])
        m = fixtures_by_id.get(fid)
        if not m:
            continue
        blob = json.loads(path.read_text())
        for team_block in (blob["response"] if isinstance(blob, dict) else blob):
            team = canonical_team(team_block["team"]["name"])
            opp = m["awayTeam"] if team == m["homeTeam"] else m["homeTeam"]
            for entry in team_block["players"]:
                s = entry["statistics"][0]
                if not s["games"].get("minutes"):
                    continue
                logs[entry["player"]["id"]].append({
                    "fixture_id": fid, "date": m["date"], "round": m["round"], "opponent": opp,
                    "home": team == m["homeTeam"],
                    "score": f'{m["homeScore"]}-{m["awayScore"]}',
                    "minutes": s["games"]["minutes"],
                    "rating": float(s["games"]["rating"]) if s["games"].get("rating") else None,
                    "goals": _f(s["goals"].get("total")), "assists": _f(s["goals"].get("assists")),
                    "shots": _f(s["shots"].get("total")), "key_passes": _f(s["passes"].get("key")),
                })
    for pid, entries in logs.items():
        if pid in players:
            players[pid]["recent"] = sorted(entries, key=lambda e: e["date"], reverse=True)
    (SNAP / "players.json").write_text(json.dumps({"season": season, "players": list(players.values())}))
    print(f"players: {len(players)} (with match logs: {sum(1 for p in players.values() if p.get('recent'))})")

    # ---- injuries: one row per player with every missed-fixture date (spells derived at runtime)
    inj_raw = RAW / f"injuries_season{season}.json"
    if inj_raw.exists():
        by_player: dict[int, dict] = {}
        for r in sorted(json.loads(inj_raw.read_text()), key=lambda r: r["fixture"]["date"]):
            if r["league"]["id"] != 140:
                continue
            pid = r["player"]["id"]
            row = by_player.setdefault(pid, {
                "player_id": pid, "player": r["player"]["name"], "photo": r["player"].get("photo"),
                "team": canonical_team(r["team"]["name"]), "team_logo": r["team"]["logo"], "absences": [],
            })
            row["team"] = canonical_team(r["team"]["name"])
            row["absences"].append({"date": r["fixture"]["date"][:10], "type": r["player"].get("type"),
                                    "reason": r["player"].get("reason")})
        (SNAP / "injuries.json").write_text(json.dumps({"season": season, "injuries": list(by_player.values())}))
        print(f"injury records: {len(by_player)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="download missing raw responses")
    ap.add_argument("--player-logs", type=int, default=0, help="rounds of per-match player stats to fetch")
    args = ap.parse_args()
    if args.fetch:
        fetch_all()
        if args.player_logs:
            fetch_player_logs(args.player_logs)
    process()
