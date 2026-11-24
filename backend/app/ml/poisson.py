"""Dixon-Coles bivariate Poisson model with time decay.

Fixes over the previous implementation:
* home/away win were swapped (np.triu was summed as "home win" although rows are home goals)
* fitting used numerical gradients + SLSQP; now L-BFGS-B with an analytic gradient (~20x faster)
* a small ridge penalty makes the attack/defence parameters identifiable and shrinks teams
  with few matches (promoted sides) towards the league average
* all goal markets are derived from one normalised score matrix so they are mutually consistent
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

MAX_GOALS = 10
DEFAULT_HALF_LIFE = 365  # days; chosen by walk-forward RPS sweep, re-validated by walk-forward RPS in train.py


def _tau(x, y, lam, mu, rho):
    tau = np.ones_like(lam, dtype=float)
    m00 = (x == 0) & (y == 0)
    m10 = (x == 1) & (y == 0)
    m01 = (x == 0) & (y == 1)
    m11 = (x == 1) & (y == 1)
    tau[m00] = 1 - lam[m00] * mu[m00] * rho
    tau[m10] = 1 + mu[m10] * rho
    tau[m01] = 1 + lam[m01] * rho
    tau[m11] = 1 - rho
    return tau, (m00, m10, m01, m11)


class DixonColes:
    def __init__(self, half_life_days: float = DEFAULT_HALF_LIFE, ridge: float = 0.05):
        self.half_life_days = half_life_days
        self.ridge = ridge
        self.teams: list[str] = []
        self.idx: dict[str, int] = {}
        self.attack = np.zeros(0)
        self.defence = np.zeros(0)
        self.home_adv = 0.25
        self.rho = 0.0
        self.is_fitted = False

    # ------------------------------------------------------------------ fit
    def fit(self, home: np.ndarray, away: np.ndarray, hg: np.ndarray, ag: np.ndarray,
            dates: pd.Series, as_of: pd.Timestamp | None = None) -> "DixonColes":
        teams = sorted(set(home) | set(away))
        self.teams, self.idx = teams, {t: i for i, t in enumerate(teams)}
        n = len(teams)
        hi = np.array([self.idx[t] for t in home])
        ai = np.array([self.idx[t] for t in away])
        x, y = np.asarray(hg, dtype=float), np.asarray(ag, dtype=float)
        as_of = as_of if as_of is not None else pd.Timestamp(dates.max())
        days = (as_of - pd.to_datetime(dates)).dt.days.to_numpy(dtype=float)
        w = np.exp(-np.log(2) * np.clip(days, 0, None) / self.half_life_days)
        ridge = self.ridge

        def nll(params):
            att, dfn = params[:n], params[n:2 * n]
            ha, rho = params[2 * n], params[2 * n + 1]
            lam = np.exp(att[hi] + dfn[ai] + ha)
            mu = np.exp(att[ai] + dfn[hi])
            tau, (m00, m10, m01, m11) = _tau(x, y, lam, mu, rho)
            tau_c = np.maximum(tau, 1e-10)
            ll = w * (x * np.log(lam) - lam + y * np.log(mu) - mu + np.log(tau_c))

            # d/dlog(lam), d/dlog(mu), d/drho of each match's log-likelihood
            g_lam = x - lam
            g_mu = y - mu
            g_rho = np.zeros_like(lam)
            g_lam[m00] += -lam[m00] * mu[m00] * rho / tau_c[m00]
            g_mu[m00] += -lam[m00] * mu[m00] * rho / tau_c[m00]
            g_rho[m00] = -lam[m00] * mu[m00] / tau_c[m00]
            g_mu[m10] += mu[m10] * rho / tau_c[m10]
            g_rho[m10] = mu[m10] / tau_c[m10]
            g_lam[m01] += lam[m01] * rho / tau_c[m01]
            g_rho[m01] = lam[m01] / tau_c[m01]
            g_rho[m11] = -1 / tau_c[m11]
            g_lam, g_mu, g_rho = w * g_lam, w * g_mu, w * g_rho

            grad = np.zeros_like(params)
            grad[:n] = np.bincount(hi, g_lam, n) + np.bincount(ai, g_mu, n)
            grad[n:2 * n] = np.bincount(ai, g_lam, n) + np.bincount(hi, g_mu, n)
            grad[2 * n] = g_lam.sum()
            grad[2 * n + 1] = g_rho.sum()

            pen = ridge * (np.sum(att ** 2) + np.sum(dfn ** 2))
            gpen = np.zeros_like(params)
            gpen[:2 * n] = 2 * ridge * params[:2 * n]
            return -ll.sum() + pen, -grad + gpen

        x0 = np.zeros(2 * n + 2)
        x0[2 * n] = 0.25
        bounds = [(-3, 3)] * (2 * n) + [(-1, 1), (-0.3, 0.3)]
        res = minimize(nll, x0, jac=True, method="L-BFGS-B", bounds=bounds, options={"maxiter": 500})
        p = res.x
        self.attack, self.defence = p[:n], p[n:2 * n]
        self.home_adv, self.rho = float(p[2 * n]), float(p[2 * n + 1])
        self.is_fitted = True
        return self

    def fit_df(self, df: pd.DataFrame, as_of: pd.Timestamp | None = None) -> "DixonColes":
        return self.fit(df["homeTeam"].to_numpy(), df["awayTeam"].to_numpy(),
                        df["homeScore"].to_numpy(), df["awayScore"].to_numpy(), df["date"], as_of)

    # ------------------------------------------------------------------ predict
    def expected_goals(self, home: str, away: str) -> tuple[float, float]:
        # Unknown (e.g. newly promoted) teams get league-average parameters (0) shifted slightly down.
        ah = self.attack[self.idx[home]] if home in self.idx else -0.15
        dh = self.defence[self.idx[home]] if home in self.idx else 0.15
        aa = self.attack[self.idx[away]] if away in self.idx else -0.15
        da = self.defence[self.idx[away]] if away in self.idx else 0.15
        lam = float(np.exp(ah + da + self.home_adv))
        mu = float(np.exp(aa + dh))
        return lam, mu

    def matrix(self, home: str, away: str, lam_mult: float = 1.0, mu_mult: float = 1.0) -> np.ndarray:
        lam, mu = self.expected_goals(home, away)
        return score_matrix(lam * lam_mult, mu * mu_mult, self.rho)

    def predict_1x2(self, home: str, away: str) -> np.ndarray:
        """Returns [P(draw), P(home), P(away)] (class order used by every model in the ensemble)."""
        m = self.matrix(home, away)
        return np.array([np.trace(m), np.tril(m, -1).sum(), np.triu(m, 1).sum()])

    def team_ratings(self) -> list[dict]:
        return [{"team": t, "attack": round(float(np.exp(self.attack[i])), 3),
                 "defence": round(float(np.exp(self.defence[i])), 3)} for t, i in self.idx.items()]


def score_matrix(lam: float, mu: float, rho: float, max_goals: int = MAX_GOALS) -> np.ndarray:
    """P(home = i, away = j); rows are HOME goals, columns AWAY goals."""
    g = np.arange(max_goals + 1)
    m = np.outer(poisson.pmf(g, lam), poisson.pmf(g, mu))
    m[0, 0] *= 1 - lam * mu * rho
    m[1, 0] *= 1 + mu * rho
    m[0, 1] *= 1 + lam * rho
    m[1, 1] *= 1 - rho
    m = np.clip(m, 0, None)
    return m / m.sum()


def outcome_probs(m: np.ndarray) -> dict:
    return {"home_win": float(np.tril(m, -1).sum()), "draw": float(np.trace(m)), "away_win": float(np.triu(m, 1).sum())}


def reweight_to_outcomes(m: np.ndarray, target: dict) -> np.ndarray:
    """Rescale the matrix so its 1X2 marginals equal the ensemble's, keeping the scoreline
    shape within each outcome. Makes markets/scorelines consistent with the headline odds."""
    cur = outcome_probs(m)
    out = m.copy()
    home_mask = np.tril(np.ones_like(m, dtype=bool), -1)
    away_mask = np.triu(np.ones_like(m, dtype=bool), 1)
    draw_mask = np.eye(m.shape[0], dtype=bool)
    for mask, key in ((home_mask, "home_win"), (away_mask, "away_win"), (draw_mask, "draw")):
        if cur[key] > 0:
            out[mask] *= target[key] / cur[key]
    return out / out.sum()


def markets(m: np.ndarray) -> dict:
    n = m.shape[0]
    total = np.add.outer(np.arange(n), np.arange(n))
    p_total = np.array([m[total == k].sum() for k in range(2 * n - 1)])
    over = lambda line: float(m[total > line].sum())  # noqa: E731
    home_cs = float(m[:, 0].sum())   # away scores 0
    away_cs = float(m[0, :].sum())   # home scores 0
    btts = float(m[1:, 1:].sum())
    res = outcome_probs(m)
    margin = {}
    diff = np.subtract.outer(np.arange(n), np.arange(n))
    for d in range(-3, 4):
        if d == -3:
            margin["away_3plus"] = float(m[diff <= -3].sum())
        elif d == 3:
            margin["home_3plus"] = float(m[diff >= 3].sum())
        else:
            key = "draw" if d == 0 else (f"home_by_{d}" if d > 0 else f"away_by_{-d}")
            margin[key] = float(m[diff == d].sum())
    return {
        "over_0_5": over(0.5), "over_1_5": over(1.5), "over_2_5": over(2.5),
        "over_3_5": over(3.5), "over_4_5": over(4.5),
        "under_1_5": 1 - over(1.5), "under_2_5": 1 - over(2.5), "under_3_5": 1 - over(3.5),
        "btts_yes": btts, "btts_no": 1 - btts,
        "home_clean_sheet": home_cs, "away_clean_sheet": away_cs,
        "home_to_score": 1 - away_cs, "away_to_score": 1 - home_cs,
        "double_chance_1x": res["home_win"] + res["draw"],
        "double_chance_x2": res["away_win"] + res["draw"],
        "double_chance_12": res["home_win"] + res["away_win"],
        "draw_no_bet_home": res["home_win"] / max(1e-9, res["home_win"] + res["away_win"]),
        "total_goals_dist": [float(p) for p in p_total[:7]] + [float(p_total[7:].sum())],
        "winning_margin": margin,
        "home_goals_dist": [float(p) for p in m.sum(axis=1)[:5]] + [float(m.sum(axis=1)[5:].sum())],
        "away_goals_dist": [float(p) for p in m.sum(axis=0)[:5]] + [float(m.sum(axis=0)[5:].sum())],
    }


def top_scorelines(m: np.ndarray, k: int = 10) -> list[dict]:
    flat = np.argsort(m, axis=None)[::-1][:k]
    out = []
    for f in flat:
        i, j = np.unravel_index(f, m.shape)
        out.append({"score": f"{i}-{j}", "home": int(i), "away": int(j), "prob": float(m[i, j])})
    return out
