from fastapi import APIRouter, Depends, Query

from ..ml.registry import registry
from ..services import injuries, team_stats
from ..services.data_store import get_store
from .deps import resolve_team_or_404

router = APIRouter(tags=["teams"])


@router.get("/teams")
def teams(all_seasons: bool = False):
    store = get_store()
    names = store.all_teams() if all_seasons else store.current_teams()
    model = registry.model
    out = []
    for t in names:
        meta = store.team_meta(t)
        out.append({"name": t, "logo": meta.get("logo"), "id": meta.get("id"), "code": meta.get("code"),
                    "venue": meta.get("venue"),
                    "elo": round(model.state.elo.rating(t), 1) if model else None})
    # `teams` (names) kept for backwards compatibility with the old frontend
    return {"teams": names, "items": out, "season": store.latest_season}


@router.get("/teams/{team}/analysis")
def team_analysis(team: str):
    store = get_store()
    team = resolve_team_or_404(team)
    model = registry.model
    elo_hist = model.state.elo.history.get(team, []) if model else []
    ratings = next((r for r in model.poisson.team_ratings() if r["team"] == team), None) if model else None
    data = team_stats.team_analysis(store, team, elo_hist, ratings)
    data["elo"] = round(model.state.elo.rating(team), 1) if model else None
    data["squad"] = sorted((p for p in store.players if p["team"] == team), key=lambda p: -p["minutes"])
    data["squad"] = [{k: p.get(k) for k in ("id", "name", "photo", "position", "age", "appearances", "minutes", "goals", "assists", "rating")} for p in data["squad"]]
    data["injuries"] = injuries.tracker(store, team)["current"]
    data["availability_impact"] = injuries.team_impact(store, team)
    return data


@router.get("/h2h")
def h2h(home: str = Query(...), away: str = Query(...), limit: int = Query(10, ge=1, le=30)):
    return team_stats.head_to_head(get_store(), resolve_team_or_404(home), resolve_team_or_404(away), limit)


@router.get("/standings")
def standings(season: int | None = None):
    return team_stats.standings(get_store(), season)


@router.get("/power-rankings")
def power_rankings():
    """Model-based ranking: Elo + Dixon-Coles attack/defence strengths for the current teams."""
    store = get_store()
    model = registry.model
    if model is None:
        return {"items": []}
    ratings = {r["team"]: r for r in model.poisson.team_ratings()}
    items = []
    for t in store.current_teams():
        r = ratings.get(t, {"attack": 1.0, "defence": 1.0})
        items.append({"team": t, "logo": store.team_meta(t).get("logo"), "elo": round(model.state.elo.rating(t), 1),
                      "attack": r["attack"], "defence": r["defence"],
                      "net_rating": round(r["attack"] / r["defence"], 3)})
    items.sort(key=lambda r: -r["elo"])
    for i, r in enumerate(items, 1):
        r["rank"] = i
    return {"items": items}
