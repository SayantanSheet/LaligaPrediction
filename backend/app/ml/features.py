"""Single feature builder shared by training and inference.

Matches are replayed in chronological order. For every match the feature row is computed from
the state *before* the match and only then is the state updated, so features never contain the
result they are trying to predict. Inference calls the same `row()` on the final state, which
removes the train/serve skew of the previous implementation (5-game rolling window in training
vs 10-game averages at prediction time).
"""
from __future__ import annotations

from collections import defaultdict, deque

import numpy as np
import pandas as pd

from .elo import Elo

LEAGUE_GOALS = 1.3
LEAGUE_PPG = 1.37

FEATURES = [
    "elo_diff", "home_elo", "away_elo",
    "h_gf5", "h_ga5", "h_ppg5", "a_gf5", "a_ga5", "a_ppg5",
    "h_gf10", "h_ga10", "a_gf10", "a_ga10",
    "h_home_ppg", "h_home_gf", "a_away_ppg", "a_away_gf",
    "h_rest", "a_rest", "h2h_home_ppg",
]


def _mean(values, default: float, n: int | None = None) -> float:
    vals = list(values)[-n:] if n else list(values)
    return float(np.mean(vals)) if vals else default


def _deque10():
    return deque(maxlen=10)


def _deque6():
    return deque(maxlen=6)


class FeatureState:
    def __init__(self):
        self.elo = Elo()
        self.recent = defaultdict(_deque10)       # (gf, ga, pts)
        self.home_recent = defaultdict(_deque10)  # games at home
        self.away_recent = defaultdict(_deque10)  # games away
        self.last_date: dict[str, pd.Timestamp] = {}
        self.h2h = defaultdict(_deque6)           # key (a,b) sorted -> (winner or None)

    def row(self, home: str, away: str, date: pd.Timestamp) -> dict:
        h, a = self.recent[home], self.recent[away]
        hr = self.home_recent[home]
        ar = self.away_recent[away]

        def rest(team):
            last = self.last_date.get(team)
            return float(min(21, (date - last).days)) if last is not None else 14.0

        key = tuple(sorted((home, away)))
        meetings = list(self.h2h[key])
        h2h_pts = [3 if w == home else 1 if w is None else 0 for w in meetings]
        he, ae = self.elo.rating(home), self.elo.rating(away)
        return {
            "elo_diff": he - ae, "home_elo": he, "away_elo": ae,
            "h_gf5": _mean((g[0] for g in h), LEAGUE_GOALS, 5),
            "h_ga5": _mean((g[1] for g in h), LEAGUE_GOALS, 5),
            "h_ppg5": _mean((g[2] for g in h), LEAGUE_PPG, 5),
            "a_gf5": _mean((g[0] for g in a), LEAGUE_GOALS, 5),
            "a_ga5": _mean((g[1] for g in a), LEAGUE_GOALS, 5),
            "a_ppg5": _mean((g[2] for g in a), LEAGUE_PPG, 5),
            "h_gf10": _mean((g[0] for g in h), LEAGUE_GOALS),
            "h_ga10": _mean((g[1] for g in h), LEAGUE_GOALS),
            "a_gf10": _mean((g[0] for g in a), LEAGUE_GOALS),
            "a_ga10": _mean((g[1] for g in a), LEAGUE_GOALS),
            "h_home_ppg": _mean((g[2] for g in hr), 1.6),
            "h_home_gf": _mean((g[0] for g in hr), 1.5),
            "a_away_ppg": _mean((g[2] for g in ar), 1.1),
            "a_away_gf": _mean((g[0] for g in ar), 1.1),
            "h_rest": rest(home), "a_rest": rest(away),
            "h2h_home_ppg": _mean(h2h_pts, LEAGUE_PPG),
        }

    def update(self, home: str, away: str, hg: int, ag: int, date: pd.Timestamp, season: int | None) -> None:
        hp = 3 if hg > ag else 1 if hg == ag else 0
        ap = 3 if ag > hg else 1 if hg == ag else 0
        self.recent[home].append((hg, ag, hp))
        self.recent[away].append((ag, hg, ap))
        self.home_recent[home].append((hg, ag, hp))
        self.away_recent[away].append((ag, hg, ap))
        self.last_date[home] = self.last_date[away] = date
        winner = home if hg > ag else away if ag > hg else None
        self.h2h[tuple(sorted((home, away)))].append(winner)
        self.elo.update(home, away, int(hg), int(ag), str(date.date()), season)


def build_training_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, FeatureState]:
    """Return (features + target per match, final state). `df` must be sorted by date."""
    state = FeatureState()
    rows = []
    for m in df.itertuples(index=False):
        r = state.row(m.homeTeam, m.awayTeam, m.date)
        r["outcome"] = 1 if m.homeScore > m.awayScore else 2 if m.homeScore < m.awayScore else 0
        rows.append(r)
        state.update(m.homeTeam, m.awayTeam, m.homeScore, m.awayScore, m.date, getattr(m, "season", None))
    out = pd.DataFrame(rows, index=df.index)
    return out, state
