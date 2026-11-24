"""Builds the full match-analysis payload from the ensemble + team/player services."""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from ..ml import poisson as pm
from ..ml.registry import registry
from . import injuries as inj
from . import team_stats
from .data_store import get_store

MODEL_LABELS = {"xgboost": "XGBoost", "lightgbm": "LightGBM", "random_forest": "Random Forest", "poisson": "Dixon-Coles Poisson"}


def _pct(x: float) -> float:
    return round(100 * float(x), 1)


def _outcome_key(p: dict) -> str:
    return max(("home_win", "draw", "away_win"), key=lambda k: p[k])


def _factors(home: str, away: str, f: dict, h2h: dict, impact_h: dict, impact_a: dict, xg: dict) -> list[dict]:
    """Human-readable drivers of the prediction, signed towards home (+) or away (-)."""
    out = []
    elo = f["elo_diff"]
    out.append({"label": "Team strength (Elo)", "detail": f"{home} {f['home_elo']:.0f} vs {away} {f['away_elo']:.0f}",
                "direction": "home" if elo > 25 else "away" if elo < -25 else "neutral", "weight": round(min(1, abs(elo) / 250), 2)})
    form = f["h_ppg5"] - f["a_ppg5"]
    out.append({"label": "Recent form (last 5)", "detail": f"{f['h_ppg5']:.1f} vs {f['a_ppg5']:.1f} points per game",
                "direction": "home" if form > 0.3 else "away" if form < -0.3 else "neutral", "weight": round(min(1, abs(form) / 2), 2)})
    venue = f["h_home_ppg"] - f["a_away_ppg"]
    out.append({"label": "Venue record", "detail": f"{home} home {f['h_home_ppg']:.2f} PPG · {away} away {f['a_away_ppg']:.2f} PPG",
                "direction": "home" if venue > 0.3 else "away" if venue < -0.3 else "neutral", "weight": round(min(1, abs(venue) / 2), 2)})
    xgd = xg["home"] - xg["away"]
    out.append({"label": "Expected goals", "detail": f"{xg['home']:.2f} vs {xg['away']:.2f}",
                "direction": "home" if xgd > 0.25 else "away" if xgd < -0.25 else "neutral", "weight": round(min(1, abs(xgd) / 1.5), 2)})
    if h2h["played"]:
        d = h2h["team_a_wins"] - h2h["team_b_wins"]
        out.append({"label": "Head-to-head", "detail": f"{h2h['team_a_wins']}W {h2h['draws']}D {h2h['team_b_wins']}L in {h2h['played']} meetings",
                    "direction": "home" if d > 0 else "away" if d < 0 else "neutral", "weight": round(min(1, abs(d) / max(1, h2h["played"])), 2)})
    if impact_h["players"] or impact_a["players"]:
        loss_h, loss_a = 1 - impact_h["attack_multiplier"], 1 - impact_a["attack_multiplier"]
        out.append({"label": "Availability", "detail": f"{len(impact_h['players'])} {home} / {len(impact_a['players'])} {away} key absences",
                    "direction": "away" if loss_h > loss_a + 0.01 else "home" if loss_a > loss_h + 0.01 else "neutral",
                    "weight": round(min(1, abs(loss_h - loss_a) * 8), 2)})
    rest = f["h_rest"] - f["a_rest"]
    if abs(rest) >= 3:
        out.append({"label": "Rest days", "detail": f"{f['h_rest']:.0f} vs {f['a_rest']:.0f} days since last match",
                    "direction": "home" if rest > 0 else "away", "weight": 0.2})
    return out


def _team_card(store, home_or_away_team: str, model, impact: dict) -> dict:
    m = team_stats.team_matches(store.matches_df, home_or_away_team)
    season = m[m.season == store.latest_season]
    split = team_stats._split(season if len(season) else m.tail(38))
    ratings = next((r for r in model.poisson.team_ratings() if r["team"] == home_or_away_team), None)
    players = sorted((p for p in store.players if p["team"] == home_or_away_team), key=lambda p: -(p["goals"] + p["assists"]))
    return {
        "team": home_or_away_team, "logo": store.team_meta(home_or_away_team).get("logo"),
        "elo": round(model.state.elo.rating(home_or_away_team), 1),
        "form": team_stats.form_list(m, 5), "form_string": "".join(m.result.tail(5).tolist()),
        "season": split, "ratings": ratings,
        "key_players": [{"id": p["id"], "name": p["name"], "photo": p.get("photo"), "position": p["position"],
                         "goals": p["goals"], "assists": p["assists"], "rating": p.get("rating")} for p in players[:3]],
        "unavailable": impact["players"],
    }


@lru_cache(maxsize=512)
def _predict_cached(home: str, away: str, version: str, use_availability: bool) -> dict:
    store = get_store()
    model = registry.model
    if use_availability:
        imp_h = inj.team_impact(store, home)
        imp_a = inj.team_impact(store, away)
    else:
        imp_h = imp_a = {"attack_multiplier": 1.0, "opponent_attack_multiplier": 1.0, "players": []}
    lam_mult = imp_h["attack_multiplier"] * imp_a["opponent_attack_multiplier"]
    mu_mult = imp_a["attack_multiplier"] * imp_h["opponent_attack_multiplier"]
    r = model.predict(home, away, lam_mult, mu_mult)
    probs = r["ensemble"]
    matrix = r["matrix"]
    mk = pm.markets(matrix)
    top = pm.top_scorelines(matrix, 10)
    pick = _outcome_key(probs)
    base_picks = [_outcome_key(v) for v in r["base"].values()]
    agree = sum(1 for b in base_picks if b == pick)
    spread = float(np.std([v[pick] for v in r["base"].values()]))
    h2h = team_stats.head_to_head(store, home, away, 6)
    conf = probs[pick]

    return {
        "home_team": home, "away_team": away,
        "home_logo": store.team_meta(home).get("logo"), "away_logo": store.team_meta(away).get("logo"),
        "probabilities": {k: _pct(v) for k, v in probs.items()},
        "probabilities_without_availability": {k: _pct(v) for k, v in r["ensemble_unadjusted"].items()},
        "predicted_outcome": {"home_win": "H", "draw": "D", "away_win": "A"}[pick],
        "predicted_outcome_label": {"home_win": f"{home} win", "draw": "Draw", "away_win": f"{away} win"}[pick],
        "predicted_score": top[0]["score"],
        "confidence": _pct(conf),
        "confidence_level": "high" if conf >= 0.6 else "medium" if conf >= 0.45 else "low",
        "expected_goals": {"home": round(r["xg"]["home"], 2), "away": round(r["xg"]["away"], 2),
                           "home_base": round(r["xg"]["home_base"], 2), "away_base": round(r["xg"]["away_base"], 2)},
        "markets": {k: (_pct(v) if isinstance(v, float) else [_pct(x) for x in v] if isinstance(v, list) else {kk: _pct(vv) for kk, vv in v.items()})
                    for k, v in mk.items()},
        "scorelines": [{**s, "prob": _pct(s["prob"])} for s in top],
        "score_matrix": [[_pct(matrix[i, j]) for j in range(6)] for i in range(6)],
        "models": [{"key": k, "name": MODEL_LABELS[k], **{kk: _pct(vv) for kk, vv in v.items()}} for k, v in r["base"].items()],
        "model_agreement": {"agreeing_models": agree, "total_models": len(base_picks),
                            "level": "high" if agree == len(base_picks) and spread < 0.05 else "medium" if agree >= len(base_picks) - 1 else "low",
                            "spread": _pct(spread)},
        "availability": {"home": imp_h, "away": imp_a, "applied": use_availability},
        "factors": _factors(home, away, r["features"], h2h, imp_h, imp_a, r["xg"]),
        "teams": {"home": _team_card(store, home, model, imp_h), "away": _team_card(store, away, model, imp_a)},
        "h2h": h2h,
        "model_version": version,
    }


def predict(home: str, away: str, use_availability: bool = True) -> dict:
    return _predict_cached(home, away, registry.model.data_version + f"@{registry.model.metrics.get('trained_at', '')}", use_availability)


def quick_pick(home: str, away: str) -> dict | None:
    """Lightweight prediction for fixture lists (unknown/promoted teams are allowed)."""
    model = registry.model
    if model is None:
        return None
    try:
        r = model.predict(home, away)
    except Exception:
        return None
    p = r["ensemble"]
    top = pm.top_scorelines(r["matrix"], 1)[0]
    return {"home_win": _pct(p["home_win"]), "draw": _pct(p["draw"]), "away_win": _pct(p["away_win"]),
            "predicted_score": top["score"], "pick": {"home_win": "H", "draw": "D", "away_win": "A"}[_outcome_key(p)],
            "over_2_5": _pct(pm.markets(r["matrix"])["over_2_5"]), "btts": _pct(pm.markets(r["matrix"])["btts_yes"])}
