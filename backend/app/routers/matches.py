from fastapi import APIRouter

from ..services import fixtures
from ..services.data_store import get_store
from ..services.prediction import quick_pick

router = APIRouter(tags=["matches"])


def _with_picks(rows: list[dict]) -> list[dict]:
    store = get_store()
    for r in rows:
        if r.get("status") in fixtures.UPCOMING:
            h, a = store.resolve_team(r["home_team"]), store.resolve_team(r["away_team"])
            r["prediction"] = quick_pick(h or r["home_team"], a or r["away_team"])
    return rows


@router.get("/fixtures/live")
def live():
    return fixtures.live()


@router.get("/fixtures/upcoming")
def upcoming():
    data = fixtures.upcoming()
    data["matches"] = _with_picks(data["matches"])
    return data


@router.get("/fixtures/results")
def results(limit: int = 30):
    """Today's/yesterday's results from the API plus the latest results in the data set."""
    store = get_store()
    api = fixtures.recent_results()
    df = store.matches_df.tail(limit).iloc[::-1]
    history = [{
        "id": int(r.id), "date": r.date.strftime("%Y-%m-%d"), "round": f"Matchday {r.round}" if getattr(r, "round", None) else None,
        "season": int(r.season), "home_team": r.homeTeam, "away_team": r.awayTeam,
        "home_logo": store.team_meta(r.homeTeam).get("logo"), "away_logo": store.team_meta(r.awayTeam).get("logo"),
        "home_score": int(r.homeScore), "away_score": int(r.awayScore),
        "halftime": {"home": None if r.homeHT != r.homeHT else int(r.homeHT), "away": None if r.awayHT != r.awayHT else int(r.awayHT)},
        "venue": getattr(r, "venue", None),
    } for r in df.itertuples()]
    return {"live_api": api, "history": history, "data_as_of": store.data_as_of}


@router.get("/fixtures/simulate-round")
def simulate_round():
    """Model picks for a full round of fixtures: the reverse of the most recent matchday in the data set
    (used on the dashboard when the free API plan exposes no upcoming LaLiga fixtures)."""
    store = get_store()
    df = store.matches_df
    if df.empty:
        return {"matches": []}
    last = df[df.season == df.season.max()]
    last_round = last[last["round"] == last["round"].iloc[-1]] if "round" in last else last.tail(10)
    rows = []
    for r in last_round.itertuples():
        home, away = r.awayTeam, r.homeTeam
        rows.append({"home_team": home, "away_team": away,
                     "home_logo": store.team_meta(home).get("logo"), "away_logo": store.team_meta(away).get("logo"),
                     "prediction": quick_pick(home, away)})
    return {"label": "Model simulation: reverse fixtures of the latest matchday", "matches": rows}
