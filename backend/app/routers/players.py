from fastapi import APIRouter, HTTPException, Query

from ..services import injuries, player_stats
from ..services.data_store import get_store

router = APIRouter(tags=["players"])


@router.get("/players")
def players(team: str | None = None, position: str | None = None, q: str | None = None,
            sort: str = "rating", min_minutes: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=1000)):
    store = get_store()
    if team:
        team = store.resolve_team(team) or team
    return {"season": store.players_season,
            "items": player_stats.list_players(store, team, position, q, sort, min_minutes, limit)}


@router.get("/players/leaders")
def leaders(limit: int = Query(10, ge=1, le=50)):
    return player_stats.leaders(get_store(), limit)


@router.get("/players/compare")
def compare(a: int, b: int):
    res = player_stats.compare(get_store(), a, b)
    if res is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return res


@router.get("/players/{player_id}")
def player(player_id: int):
    store = get_store()
    res = player_stats.profile(store, player_id)
    if res is None:
        raise HTTPException(status_code=404, detail="Player not found")
    res["availability"] = next((e for e in injuries.tracker(store, res["team"])["current"] if e["player_id"] == player_id), None)
    return res


@router.get("/injuries")
def injury_tracker(team: str | None = None, history: bool = False):
    store = get_store()
    if team:
        team = store.resolve_team(team) or team
    data = injuries.tracker(store, team, include_history=history)
    teams = sorted({e["team"] for e in data["current"]})
    data["impact"] = {t: injuries.team_impact(store, t) for t in teams}
    return data
