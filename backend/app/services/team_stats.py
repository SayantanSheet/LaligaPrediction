"""Team-level analytics computed from the match history."""
from __future__ import annotations

import pandas as pd

from .data_store import DataStore


def _result(gf: int, ga: int) -> str:
    return "W" if gf > ga else "D" if gf == ga else "L"


def team_matches(df: pd.DataFrame, team: str) -> pd.DataFrame:
    """One row per match from `team`'s perspective, oldest first."""
    m = df[(df.homeTeam == team) | (df.awayTeam == team)].copy()
    home = m.homeTeam == team
    m["venue_side"] = home.map({True: "home", False: "away"})
    m["opponent"] = m.awayTeam.where(home, m.homeTeam)
    m["gf"] = m.homeScore.where(home, m.awayScore).astype(int)
    m["ga"] = m.awayScore.where(home, m.homeScore).astype(int)
    m["gf_ht"] = m.homeHT.where(home, m.awayHT) if "homeHT" in m else None
    m["ga_ht"] = m.awayHT.where(home, m.homeHT) if "awayHT" in m else None
    m["result"] = [_result(a, b) for a, b in zip(m.gf, m.ga)]
    m["points"] = m.result.map({"W": 3, "D": 1, "L": 0})
    return m


def _split(m: pd.DataFrame) -> dict:
    n = len(m)
    if n == 0:
        return {"played": 0}
    return {
        "played": n,
        "won": int((m.result == "W").sum()), "drawn": int((m.result == "D").sum()), "lost": int((m.result == "L").sum()),
        "goals_for": int(m.gf.sum()), "goals_against": int(m.ga.sum()),
        "points": int(m.points.sum()), "ppg": round(float(m.points.mean()), 2),
        "avg_scored": round(float(m.gf.mean()), 2), "avg_conceded": round(float(m.ga.mean()), 2),
        "win_rate": round(float((m.result == "W").mean()), 3),
        "clean_sheets": int((m.ga == 0).sum()), "failed_to_score": int((m.gf == 0).sum()),
        "btts_rate": round(float(((m.gf > 0) & (m.ga > 0)).mean()), 3),
        "over_1_5_rate": round(float(((m.gf + m.ga) > 1.5).mean()), 3),
        "over_2_5_rate": round(float(((m.gf + m.ga) > 2.5).mean()), 3),
        "over_3_5_rate": round(float(((m.gf + m.ga) > 3.5).mean()), 3),
    }


def form_list(m: pd.DataFrame, n: int) -> list[dict]:
    out = []
    for r in m.tail(n).iloc[::-1].itertuples():
        out.append({"date": r.date.strftime("%Y-%m-%d"), "opponent": r.opponent, "venue": r.venue_side,
                    "score": f"{r.gf}-{r.ga}", "result": r.result, "round": getattr(r, "round", None)})
    return out


def standings(store: DataStore, season: int | None = None) -> dict:
    df = store.matches_df
    if df.empty:
        return {"season": None, "table": []}
    season = season or store.latest_season
    sdf = df[df.season == season]
    teams = sorted(set(sdf.homeTeam) | set(sdf.awayTeam))
    rows = []
    for t in teams:
        m = team_matches(sdf, t)
        s = _split(m)
        rows.append({
            "team": t, "logo": store.team_meta(t).get("logo"),
            "played": s["played"], "won": s["won"], "drawn": s["drawn"], "lost": s["lost"],
            "goals_for": s["goals_for"], "goals_against": s["goals_against"],
            "goal_diff": s["goals_for"] - s["goals_against"], "points": s["points"],
            "form": "".join(m.result.tail(5).tolist()),
            "home_points": int(m[m.venue_side == "home"].points.sum()),
            "away_points": int(m[m.venue_side == "away"].points.sum()),
        })
    # LaLiga tie-break is head-to-head; goal difference is a close approximation for display.
    rows.sort(key=lambda r: (-r["points"], -r["goal_diff"], -r["goals_for"], r["team"]))
    n = len(rows)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
        r["zone"] = ("champions_league" if i <= 4 else "europa_league" if i <= 6 else
                     "conference_league" if i == 7 else "relegation" if i > n - 3 else None)
    seasons = sorted(int(s) for s in df.season.unique())
    return {"season": int(season), "seasons": seasons, "table": rows}


def team_analysis(store: DataStore, team: str, elo_history: list | None = None,
                  ratings: dict | None = None) -> dict:
    df = store.matches_df
    season = store.latest_season
    all_m = team_matches(df, team)
    cur = all_m[all_m.season == season] if not all_m[all_m.season == season].empty else all_m.tail(38)
    table = standings(store, season)["table"]
    pos = next((r for r in table if r["team"] == team), None)

    trend = []
    roll = cur.assign(roll_gf=cur.gf.rolling(5, min_periods=1).mean(), roll_ga=cur.ga.rolling(5, min_periods=1).mean(),
                      cum_pts=cur.points.cumsum())
    for i, r in enumerate(roll.itertuples(), 1):
        trend.append({"match": i, "date": r.date.strftime("%Y-%m-%d"), "opponent": r.opponent, "gf": r.gf, "ga": r.ga,
                      "roll_gf": round(r.roll_gf, 2), "roll_ga": round(r.roll_ga, 2), "points": int(r.cum_pts)})

    halves = {}
    if cur.gf_ht is not None and cur.gf_ht.notna().any():
        halves = {
            "first_half_for": int(cur.gf_ht.sum()), "second_half_for": int((cur.gf - cur.gf_ht).sum()),
            "first_half_against": int(cur.ga_ht.sum()), "second_half_against": int((cur.ga - cur.ga_ht).sum()),
            "leading_at_ht": int((cur.gf_ht > cur.ga_ht).sum()),
            "comebacks": int(((cur.gf_ht < cur.ga_ht) & (cur.result != "L")).sum()),
            "points_dropped_from_winning": int(((cur.gf_ht > cur.ga_ht) & (cur.result != "W")).sum()),
        }

    biggest_win = cur.assign(gd=cur.gf - cur.ga).sort_values("gd", ascending=False).head(1)
    streak, kind = 0, None
    for r in cur.result.iloc[::-1]:
        if kind is None:
            kind = r
        if r != kind:
            break
        streak += 1

    return {
        "team": team, "meta": store.team_meta(team), "season": season,
        "position": pos, "overall": _split(cur),
        "home": _split(cur[cur.venue_side == "home"]), "away": _split(cur[cur.venue_side == "away"]),
        "all_seasons": _split(all_m),
        "form": form_list(all_m, 10), "form_string": "".join(all_m.result.tail(5).tolist()),
        "streak": {"type": kind, "length": streak},
        "trend": trend, "halves": halves,
        "biggest_win": form_list(biggest_win, 1)[0] if len(biggest_win) else None,
        "elo_history": [{"date": d, "elo": e} for d, e in (elo_history or [])],
        "ratings": ratings,
    }


def head_to_head(store: DataStore, home: str, away: str, limit: int = 10) -> dict:
    df = store.matches_df
    m = df[((df.homeTeam == home) & (df.awayTeam == away)) | ((df.homeTeam == away) & (df.awayTeam == home))]
    m = m.sort_values("date")
    home_w = int((((m.homeTeam == home) & (m.homeScore > m.awayScore)) | ((m.awayTeam == home) & (m.awayScore > m.homeScore))).sum())
    away_w = int((((m.homeTeam == away) & (m.homeScore > m.awayScore)) | ((m.awayTeam == away) & (m.awayScore > m.homeScore))).sum())
    draws = int((m.homeScore == m.awayScore).sum())
    goals_home = int(m.homeScore.where(m.homeTeam == home, m.awayScore).sum())
    goals_away = int(m.awayScore.where(m.homeTeam == home, m.homeScore).sum())
    meetings = [{
        "date": r.date.strftime("%Y-%m-%d"), "season": int(r.season), "home_team": r.homeTeam, "away_team": r.awayTeam,
        "home_score": int(r.homeScore), "away_score": int(r.awayScore),
        "winner": r.homeTeam if r.homeScore > r.awayScore else r.awayTeam if r.awayScore > r.homeScore else None,
    } for r in m.tail(limit).iloc[::-1].itertuples()]
    n = len(m)
    return {
        "team_a": home, "team_b": away, "played": n, "team_a_wins": home_w, "team_b_wins": away_w, "draws": draws,
        "team_a_goals": goals_home, "team_b_goals": goals_away,
        "avg_goals": round(float((m.homeScore + m.awayScore).mean()), 2) if n else 0.0,
        "btts_rate": round(float(((m.homeScore > 0) & (m.awayScore > 0)).mean()), 3) if n else 0.0,
        "meetings": meetings,
    }
