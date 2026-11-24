"""Sequential Elo ratings (pre-match values only, so they can be used as leak-free features)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

BASE = 1500.0
PROMOTED = 1440.0  # newly seen teams start below average


@dataclass
class Elo:
    k: float = 20.0
    home_adv: float = 60.0
    season_regression: float = 0.2
    ratings: dict[str, float] = field(default_factory=dict)
    history: dict[str, list[tuple[str, float]]] = field(default_factory=dict)
    _season: int | None = None
    _seen: bool = False

    def rating(self, team: str) -> float:
        return self.ratings.get(team, PROMOTED if self._seen else BASE)

    def expected_home(self, home: str, away: str) -> float:
        return 1.0 / (1.0 + 10 ** ((self.rating(away) - self.rating(home) - self.home_adv) / 400.0))

    def _maybe_new_season(self, season: int | None) -> None:
        if season is None or season == self._season:
            return
        if self._season is not None:
            self.ratings = {t: r + self.season_regression * (BASE - r) for t, r in self.ratings.items()}
        self._season = season

    def update(self, home: str, away: str, hg: int, ag: int, date: str, season: int | None = None) -> None:
        self._maybe_new_season(season)
        rh, ra = self.rating(home), self.rating(away)
        exp_h = self.expected_home(home, away)
        actual = 1.0 if hg > ag else 0.5 if hg == ag else 0.0
        gd = abs(hg - ag)
        # FiveThirtyEight-style margin-of-victory multiplier with autocorrelation damping
        winner_diff = (rh + self.home_adv - ra) if hg > ag else (ra - rh - self.home_adv)
        mov = math.log(gd + 1) * (2.2 / (0.001 * winner_diff + 2.2)) if gd > 0 else 1.0
        delta = self.k * mov * (actual - exp_h)
        self.ratings[home] = rh + delta
        self.ratings[away] = ra - delta
        self.history.setdefault(home, []).append((date, round(self.ratings[home], 1)))
        self.history.setdefault(away, []).append((date, round(self.ratings[away], 1)))
        self._seen = True
