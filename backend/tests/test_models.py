import numpy as np
import pandas as pd
import pytest

from app.ml import poisson as pm
from app.ml.elo import Elo
from app.ml.features import FEATURES, build_training_frame


def _synthetic(n_rounds=12, seed=0):
    """Round-robin league where 'Strong' is far better than everyone else."""
    rng = np.random.default_rng(seed)
    teams = ["Strong", "B", "C", "D", "E", "F"]
    attack = {"Strong": 1.0, "B": 0.0, "C": 0.0, "D": -0.1, "E": -0.1, "F": -0.2}
    rows, day, mid = [], pd.Timestamp("2023-08-01"), 1
    for r in range(n_rounds):
        for i, h in enumerate(teams):
            for a in teams[i + 1:]:
                home, away = (h, a) if (r + i) % 2 == 0 else (a, h)
                lam = np.exp(0.2 + attack[home] - attack[away] * 0.5)
                mu = np.exp(attack[away] - attack[home] * 0.5)
                rows.append({"id": mid, "date": day, "season": 2023, "homeTeam": home, "awayTeam": away,
                             "homeScore": rng.poisson(lam), "awayScore": rng.poisson(mu)})
                mid += 1
        day += pd.Timedelta(days=7)
    return pd.DataFrame(rows)


def test_score_matrix_rows_are_home_goals_and_outcomes_not_swapped():
    m = pm.score_matrix(2.5, 0.5, 0.0)
    p = pm.outcome_probs(m)
    assert abs(sum(p.values()) - 1) < 1e-9
    assert p["home_win"] > 0.6 > p["away_win"]          # regression test for the triu/tril swap
    assert m[3, 0] > m[0, 3]


def test_dixon_coles_strong_team_favoured_both_ways():
    df = _synthetic()
    dc = pm.DixonColes(365).fit_df(df)
    d, h, a = dc.predict_1x2("Strong", "F")
    assert h > a and abs(d + h + a - 1) < 1e-9
    d, h, a = dc.predict_1x2("F", "Strong")
    assert a > h
    lam, mu = dc.expected_goals("Strong", "F")
    assert lam > mu


def test_markets_are_consistent():
    m = pm.score_matrix(1.6, 1.1, -0.05)
    mk = pm.markets(m)
    assert mk["over_0_5"] >= mk["over_1_5"] >= mk["over_2_5"] >= mk["over_3_5"] >= mk["over_4_5"]
    assert abs(mk["over_2_5"] + mk["under_2_5"] - 1) < 1e-9
    assert mk["btts_yes"] <= 1 - max(mk["home_clean_sheet"], mk["away_clean_sheet"]) + 1e-9
    assert abs(sum(mk["total_goals_dist"]) - 1) < 1e-9
    assert abs(sum(mk["winning_margin"].values()) - 1) < 1e-9


def test_reweight_matches_target_outcomes_and_keeps_shape():
    m = pm.score_matrix(1.4, 1.2, 0.0)
    target = {"home_win": 0.5, "draw": 0.3, "away_win": 0.2}
    r = pm.reweight_to_outcomes(m, target)
    got = pm.outcome_probs(r)
    for k in target:
        assert got[k] == pytest.approx(target[k], abs=1e-9)
    # within the home-win region the ratio between scorelines is unchanged
    assert r[2, 1] / r[1, 0] == pytest.approx(m[2, 1] / m[1, 0])


def test_elo_is_zero_sum_and_rewards_winner():
    e = Elo()
    e.update("A", "B", 3, 0, "2024-01-01", 2024)
    assert e.rating("A") > 1500 > e.rating("B")
    assert e.rating("A") + e.rating("B") == pytest.approx(3000)


def test_features_have_no_leakage():
    df = _synthetic()
    feats, _ = build_training_frame(df)
    assert list(FEATURES) == [c for c in feats.columns if c != "outcome"]
    # Changing the result of the last match must not change that match's own features.
    df2 = df.copy()
    df2.loc[df2.index[-1], ["homeScore", "awayScore"]] = [9, 0]
    feats2, _ = build_training_frame(df2)
    pd.testing.assert_series_equal(feats.iloc[-1][FEATURES], feats2.iloc[-1][FEATURES])
    # First appearance gets neutral defaults
    assert feats.iloc[0]["elo_diff"] == 0
