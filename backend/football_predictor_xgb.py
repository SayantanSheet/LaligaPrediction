"""
Football Match Outcome Predictor — XGBoost Production Pipeline
Temporal Validation · Anti-Leakage · Calibrated Probabilities

Compatible with the existing LaLiga backend (scraper.py / predictor.py) and the
canonical CSV schema:
  date, home_team, away_team, home_goals, away_goals,
  home_xg, away_xg, home_elo, away_elo

Also accepts the JSON format used by the existing backend (homeTeam / homeScore)
via the load_json_matches() helper.

Installation
------------
pip install pandas numpy scikit-learn xgboost category-encoders

Quick start
-----------
python football_predictor_xgb.py                 # trains on synthetic data
python football_predictor_xgb.py --csv path.csv  # trains on real CSV
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from category_encoders import OrdinalEncoder
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
)
from sklearn.model_selection import TimeSeriesSplit

warnings.filterwarnings("ignore")

# --- Try to import XGBoost; fall back to LightGBM --------------------------
try:
    from xgboost import XGBClassifier as _GBClassifier
    _BACKEND = "xgboost"
except ImportError:
    try:
        from lightgbm import LGBMClassifier as _GBClassifier  # type: ignore
        _BACKEND = "lightgbm"
    except ImportError:
        raise SystemExit(
            "Neither xgboost nor lightgbm is installed.\n"
            "Run: pip install xgboost"
        )

print(f"[INFO] Using gradient-boosting backend: {_BACKEND}")


# ===========================================================================
# §1  CONSTANTS & CONFIGURATION
# ===========================================================================

OUTCOME_LABELS: dict[int, str] = {0: "Draw", 1: "Home Win", 2: "Away Win"}
FORM_WINDOW: int = 5
MAX_GOALS: int = 7
MIN_MATCHES_FOR_STATS: int = 3
N_SPLITS: int = 5
HOLDOUT_FRACTION: float = 0.15

GB_PARAMS: dict[str, Any] = {
    "n_estimators": 400,
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "gamma": 0.1,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "eval_metric": "mlogloss",
    "random_state": 42,
    "n_jobs": -1,
}

LGBM_PARAMS: dict[str, Any] = {
    "n_estimators": 400,
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
    "n_jobs": -1,
    "verbose": -1,
}


# ===========================================================================
# §2  DATA LOADING
# ===========================================================================

def load_csv_matches(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    for col, default in [
        ("home_xg", 0.0), ("away_xg", 0.0),
        ("home_elo", 1500.0), ("away_elo", 1500.0),
    ]:
        if col not in df.columns:
            df[col] = default
            print(f"[WARN] Column '{col}' not found -> filled with {default}")
    return df


def load_json_matches(path: str) -> pd.DataFrame:
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    records = []
    for m in raw:
        records.append({
            "date":       pd.to_datetime(m["date"]),
            "home_team":  " ".join(m["homeTeam"].replace("\n", " ").split()),
            "away_team":  " ".join(m["awayTeam"].replace("\n", " ").split()),
            "home_goals": int(m["homeScore"]),
            "away_goals": int(m["awayScore"]),
            "home_xg":   float(m.get("home_xg", 0.0)),
            "away_xg":   float(m.get("away_xg", 0.0)),
            "home_elo":  float(m.get("home_elo", 1500.0)),
            "away_elo":  float(m.get("away_elo", 1500.0)),
        })
    df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
    return df


def generate_synthetic_data(n_teams: int = 10, seasons: int = 3,
                             seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    team_names = [f"Team_{chr(65 + i)}" for i in range(n_teams)]
    attack  = rng.uniform(0.8, 2.2, n_teams)
    defense = rng.uniform(0.7, 1.8, n_teams)
    elo     = rng.uniform(1300, 1900, n_teams)
    records = []
    base_date = pd.Timestamp("2020-08-01")
    for season in range(seasons):
        season_start = base_date + pd.DateOffset(years=season)
        matchweek = 0
        for i, home in enumerate(team_names):
            for j, away in enumerate(team_names):
                if i == j:
                    continue
                matchweek += 1
                date = season_start + pd.DateOffset(days=matchweek * 7 // n_teams)
                lh = attack[i] * defense[j] * 1.15
                la = attack[j] * defense[i]
                hg = int(rng.poisson(lh))
                ag = int(rng.poisson(la))
                records.append({
                    "date":       date,
                    "home_team":  home,
                    "away_team":  away,
                    "home_goals": hg,
                    "away_goals": ag,
                    "home_xg":    round(float(lh), 3),
                    "away_xg":    round(float(la), 3),
                    "home_elo":   round(float(elo[i]), 1),
                    "away_elo":   round(float(elo[j]), 1),
                })
    df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
    print(f"[INFO] Synthetic dataset: {len(df)} matches · "
          f"{n_teams} teams · {seasons} seasons")
    return df


# ===========================================================================
# §3  TARGET ENCODING
# ===========================================================================

def encode_outcome(df: pd.DataFrame) -> pd.DataFrame:
    conditions = [
        df["home_goals"] == df["away_goals"],
        df["home_goals"] >  df["away_goals"],
        df["home_goals"] <  df["away_goals"],
    ]
    choices = [0, 1, 2]
    df = df.copy()
    df["outcome"] = np.select(conditions, choices, default=-1)
    assert (df["outcome"] == -1).sum() == 0, "Unclassified rows found"
    return df


# ===========================================================================
# §4  FEATURE ENGINEERING  (ZERO LEAKAGE)
# ===========================================================================

def _rolling_team_stats(df: pd.DataFrame, window: int = FORM_WINDOW,
                        ) -> pd.DataFrame:
    df = df.copy().reset_index(drop=True)
    df["_match_idx"] = df.index

    all_teams = pd.concat([df["home_team"], df["away_team"]]).unique()

    col_names = [
        "roll_ppg",
        "roll_xg_for",
        "roll_xg_ag",
        "roll_gd",
        "form_slope",
    ]

    stat_rows: list[dict] = []

    for team in all_teams:
        home_mask = df["home_team"] == team
        away_mask = df["away_team"] == team

        home_df = df[home_mask][["_match_idx", "date",
                                  "home_goals", "away_goals",
                                  "home_xg", "away_xg"]].copy()
        away_df = df[away_mask][["_match_idx", "date",
                                  "home_goals", "away_goals",
                                  "home_xg", "away_xg"]].copy()

        home_df["goals_for"]  = home_df["home_goals"]
        home_df["goals_ag"]   = home_df["away_goals"]
        home_df["xg_for"]     = home_df["home_xg"]
        home_df["xg_ag"]      = home_df["away_xg"]
        home_df["side"]       = "home"

        away_df["goals_for"]  = away_df["away_goals"]
        away_df["goals_ag"]   = away_df["home_goals"]
        away_df["xg_for"]     = away_df["away_xg"]
        away_df["xg_ag"]      = away_df["home_xg"]
        away_df["side"]       = "away"

        team_timeline = (
            pd.concat([home_df, away_df])
            .sort_values("date")
            .reset_index(drop=True)
        )

        def pts(row: pd.Series) -> int:
            gf, ga = row["goals_for"], row["goals_ag"]
            if gf > ga: return 3
            if gf == ga: return 1
            return 0

        team_timeline["ppg"]  = team_timeline.apply(pts, axis=1).astype(float)
        team_timeline["gd"]   = (team_timeline["goals_for"]
                                 - team_timeline["goals_ag"]).astype(float)

        for raw_col, stat_col in [
            ("ppg",     "roll_ppg"),
            ("xg_for",  "roll_xg_for"),
            ("xg_ag",   "roll_xg_ag"),
            ("gd",      "roll_gd"),
        ]:
            shifted = team_timeline[raw_col].shift(1)
            team_timeline[stat_col] = (
                shifted
                .rolling(window, min_periods=MIN_MATCHES_FOR_STATS)
                .mean()
            )

        ppg_shifted = team_timeline["ppg"].shift(1)

        def _slope(series: pd.Series) -> float:
            arr = series.dropna().values
            if len(arr) < 2:
                return 0.0
            x = np.arange(len(arr), dtype=float)
            return float(np.polyfit(x, arr, 1)[0])

        team_timeline["form_slope"] = (
            ppg_shifted
            .rolling(window, min_periods=2)
            .apply(_slope, raw=False)
        )

        for _, row in team_timeline.iterrows():
            stat_rows.append({
                "_match_idx": row["_match_idx"],
                "side":       row["side"],
                **{col: row[col] for col in col_names},
            })

    stats_df = pd.DataFrame(stat_rows)

    for side in ("home", "away"):
        side_df = (
            stats_df[stats_df["side"] == side]
            .drop(columns="side")
            .rename(columns={c: f"{side}_{c}" for c in col_names})
        )
        df = df.merge(side_df, on="_match_idx", how="left")

    df = df.drop(columns="_match_idx")
    return df


def build_features(df: pd.DataFrame, window: int = FORM_WINDOW,
                   ) -> tuple[pd.DataFrame, list[str]]:
    df = _rolling_team_stats(df, window)

    team_enc = OrdinalEncoder(
        cols=["home_team", "away_team"],
        handle_unknown="value",
        handle_missing="value",
    )
    df[["home_team_id", "away_team_id"]] = (
        team_enc
        .fit_transform(df[["home_team", "away_team"]])
        .values
    )

    df["elo_delta"]       = df["home_elo"]        - df["away_elo"]
    df["xg_delta"]        = df["home_xg"]         - df["away_xg"]
    df["ppg_delta"]       = df["home_roll_ppg"]   - df["away_roll_ppg"]
    df["xg_for_delta"]    = df["home_roll_xg_for"]- df["away_roll_xg_for"]
    df["xg_ag_delta"]     = df["home_roll_xg_ag"] - df["away_roll_xg_ag"]
    df["gd_delta"]        = df["home_roll_gd"]    - df["away_roll_gd"]
    df["slope_delta"]     = df["home_form_slope"] - df["away_form_slope"]

    feature_cols = [
        "home_elo", "away_elo", "home_xg", "away_xg",
        "home_team_id", "away_team_id",
        "home_roll_ppg",    "away_roll_ppg",
        "home_roll_xg_for", "away_roll_xg_for",
        "home_roll_xg_ag",  "away_roll_xg_ag",
        "home_roll_gd",     "away_roll_gd",
        "home_form_slope",  "away_form_slope",
        "elo_delta", "xg_delta", "ppg_delta",
        "xg_for_delta", "xg_ag_delta", "gd_delta", "slope_delta",
    ]

    roll_cols = [c for c in feature_cols if "roll_" in c or "slope" in c
                 or "delta" in c]
    nan_count = df[roll_cols].isna().sum().sum()
    if nan_count:
        print(f"[INFO] Imputing {nan_count} NaN rolling/delta values with 0")
    df[roll_cols] = df[roll_cols].fillna(0.0)

    return df, feature_cols


# ===========================================================================
# §5  EVALUATION METRICS
# ===========================================================================

def ranked_probability_score(y_true: np.ndarray,
                              y_proba: np.ndarray,
                              n_classes: int = 3) -> float:
    N = len(y_true)
    rps_total = 0.0
    for i in range(N):
        oh = np.zeros(n_classes)
        oh[int(y_true[i])] = 1.0
        cum_pred = np.cumsum(y_proba[i])
        cum_true = np.cumsum(oh)
        rps_total += np.sum((cum_pred - cum_true) ** 2) / (n_classes - 1)
    return rps_total / N


def evaluate_fold(y_true, y_pred, y_proba, fold):
    acc     = accuracy_score(y_true, y_pred)
    f1      = f1_score(y_true, y_pred, average="macro", zero_division=0)
    rps     = ranked_probability_score(y_true, y_proba)
    ll      = log_loss(y_true, y_proba, labels=[0, 1, 2])
    cm      = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
    prec, rec, f1c, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1, 2], zero_division=0
    )

    print(f"\n{'─'*56}")
    print(f"  FOLD {fold}  |  n={len(y_true)}")
    print(f"{'─'*56}")
    print(f"  Accuracy     : {acc:.4f}")
    print(f"  Macro F1     : {f1:.4f}")
    print(f"  RPS          : {rps:.4f}  (lower is better)")
    print(f"  Log Loss     : {ll:.4f}  (lower is better)")
    print(f"\n  Confusion Matrix (rows=true, cols=pred):")
    print(f"  {'':10s}  Draw  Home  Away")
    for r, label in enumerate(["Draw", "Home", "Away"]):
        print(f"  {label:<10s}  {cm[r,0]:4d}  {cm[r,1]:4d}  {cm[r,2]:4d}")
    print(f"\n  Per-class metrics:")
    print(f"  {'Class':<10s} {'Prec':>7} {'Recall':>7} {'F1':>7}")
    for k in range(3):
        print(f"  {OUTCOME_LABELS[k]:<10s} {prec[k]:>7.4f} {rec[k]:>7.4f}"
              f" {f1c[k]:>7.4f}")

    return {"acc": acc, "f1": f1, "rps": rps, "log_loss": ll}


# ===========================================================================
# §6  MODEL BUILDING
# ===========================================================================

def _make_classifier():
    params = LGBM_PARAMS if _BACKEND == "lightgbm" else GB_PARAMS
    clean = {k: v for k, v in params.items()
             if not (k == "use_label_encoder" and _BACKEND == "lightgbm")
             and not (k == "eval_metric" and _BACKEND == "lightgbm")
             and not (k == "verbose" and _BACKEND == "xgboost")}
    return _GBClassifier(**clean)


def _compute_sample_weights(y: np.ndarray) -> np.ndarray:
    counts = np.bincount(y, minlength=3).astype(float)
    freq   = counts / counts.sum()
    w_map  = {cls: 1.0 / (freq[cls] + 1e-9) for cls in range(3)}
    return np.array([w_map[int(yi)] for yi in y])


# ===========================================================================
# §7  TIME-SERIES CROSS-VALIDATION
# ===========================================================================

@dataclass
class CVResult:
    fold_metrics: list[dict] = field(default_factory=list)

    @property
    def mean_acc(self) -> float:
        return float(np.mean([m["acc"] for m in self.fold_metrics]))

    @property
    def mean_f1(self) -> float:
        return float(np.mean([m["f1"] for m in self.fold_metrics]))

    @property
    def mean_rps(self) -> float:
        return float(np.mean([m["rps"] for m in self.fold_metrics]))

    @property
    def mean_log_loss(self) -> float:
        return float(np.mean([m["log_loss"] for m in self.fold_metrics]))

    def summary(self) -> None:
        print(f"\n{'='*56}")
        print(f"  CROSS-VALIDATION SUMMARY  ({len(self.fold_metrics)} folds)")
        print(f"{'='*56}")
        print(f"  Mean Accuracy  : {self.mean_acc:.4f}")
        print(f"  Mean Macro F1  : {self.mean_f1:.4f}")
        print(f"  Mean RPS       : {self.mean_rps:.4f}  (lower is better)")
        print(f"  Mean Log Loss  : {self.mean_log_loss:.4f}  (lower is better)")
        print(f"\n  Expected accuracy range for football: 50-58%")


def cross_validate_model(X, y, n_splits=N_SPLITS):
    tscv   = TimeSeriesSplit(n_splits=n_splits)
    result = CVResult()
    X_arr  = X.values

    print(f"\n{'='*56}")
    print(f"  WALK-FORWARD TIME-SERIES CROSS-VALIDATION")
    print(f"  Dataset: {len(X)} matches · {n_splits} folds")
    print(f"{'='*56}")

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X_arr), start=1):
        X_tr, X_val = X_arr[train_idx], X_arr[val_idx]
        y_tr, y_val = y[train_idx],     y[val_idx]

        sw_tr = _compute_sample_weights(y_tr)
        clf   = _make_classifier()
        clf.fit(X_tr, y_tr, sample_weight=sw_tr)

        cal_size  = max(50, int(0.2 * len(X_tr)))
        cal_clf   = CalibratedClassifierCV(clf, method="isotonic", cv="prefit")
        cal_clf.fit(X_tr[-cal_size:], y_tr[-cal_size:])

        y_pred  = cal_clf.predict(X_val)
        y_proba = cal_clf.predict_proba(X_val)

        metrics = evaluate_fold(y_val, y_pred, y_proba, fold)
        result.fold_metrics.append(metrics)

    result.summary()
    return result


# ===========================================================================
# §8  FINAL MODEL TRAINING
# ===========================================================================

@dataclass
class TrainedPipeline:
    clf:          Any
    feature_cols: list[str]
    team_enc:     OrdinalEncoder
    df_train:     pd.DataFrame
    window:       int


def train_final_model(df, feature_cols, holdout_fraction=HOLDOUT_FRACTION,
                      window=FORM_WINDOW):
    n   = len(df)
    cut = int(n * (1 - holdout_fraction))

    train_df = df.iloc[:cut].copy()
    hold_df  = df.iloc[cut:].copy()

    X_tr = train_df[feature_cols].values
    y_tr = train_df["outcome"].values
    X_ho = hold_df[feature_cols].values
    y_ho = hold_df["outcome"].values

    sw_tr = _compute_sample_weights(y_tr)

    base_clf = _make_classifier()
    base_clf.fit(X_tr, y_tr, sample_weight=sw_tr)

    cal_size  = max(50, int(0.2 * len(X_tr)))
    cal_clf   = CalibratedClassifierCV(base_clf, method="isotonic", cv="prefit")
    cal_clf.fit(X_tr[-cal_size:], y_tr[-cal_size:])

    y_pred  = cal_clf.predict(X_ho)
    y_proba = cal_clf.predict_proba(X_ho)

    print(f"\n{'='*56}")
    print(f"  FINAL MODEL — HOLDOUT EVALUATION  (last {holdout_fraction:.0%})")
    ho_metrics = evaluate_fold(y_ho, y_pred, y_proba, fold=0)
    ho_metrics["n"] = len(y_ho)

    team_enc = OrdinalEncoder(
        cols=["home_team", "away_team"],
        handle_unknown="value",
        handle_missing="value",
    )
    team_enc.fit(df[["home_team", "away_team"]])

    pipeline = TrainedPipeline(
        clf=cal_clf,
        feature_cols=feature_cols,
        team_enc=team_enc,
        df_train=train_df,
        window=window,
    )
    return pipeline, ho_metrics


# ===========================================================================
# §9  INFERENCE
# ===========================================================================

def predict_match(pipeline, home_team, away_team,
                  home_elo=1500.0, away_elo=1500.0,
                  home_xg=0.0, away_xg=0.0,
                  home_ppg_override=None, away_ppg_override=None):
    df_tr = pipeline.df_train

    def _team_rolling(team):
        w    = pipeline.window
        mask = (df_tr["home_team"] == team) | (df_tr["away_team"] == team)
        tm   = df_tr[mask].sort_values("date").tail(w + 1)

        if tm.empty:
            return {"roll_ppg": 0.0, "roll_xg_for": 0.0,
                    "roll_xg_ag": 0.0, "roll_gd": 0.0, "form_slope": 0.0}

        is_home = tm["home_team"] == team
        zeros   = pd.Series(0.0, index=tm.index)

        roll_ppg = np.where(is_home, tm.get("home_roll_ppg", zeros),
                                     tm.get("away_roll_ppg", zeros))
        roll_xgf = np.where(is_home, tm.get("home_roll_xg_for", zeros),
                                     tm.get("away_roll_xg_for", zeros))
        roll_xga = np.where(is_home, tm.get("home_roll_xg_ag", zeros),
                                     tm.get("away_roll_xg_ag", zeros))
        roll_gd  = np.where(is_home, tm.get("home_roll_gd", zeros),
                                     tm.get("away_roll_gd", zeros))
        slope    = np.where(is_home, tm.get("home_form_slope", zeros),
                                     tm.get("away_form_slope", zeros))

        return {
            "roll_ppg":    float(np.nanmean(roll_ppg)  or 0),
            "roll_xg_for": float(np.nanmean(roll_xgf)  or 0),
            "roll_xg_ag":  float(np.nanmean(roll_xga)  or 0),
            "roll_gd":     float(np.nanmean(roll_gd)   or 0),
            "form_slope":  float(np.nanmean(slope)     or 0),
        }

    h = _team_rolling(home_team)
    a = _team_rolling(away_team)

    if home_ppg_override is not None:
        h["roll_ppg"] = home_ppg_override
    if away_ppg_override is not None:
        a["roll_ppg"] = away_ppg_override

    ids   = pipeline.team_enc.transform(
        pd.DataFrame([[home_team, away_team]],
                     columns=["home_team", "away_team"])
    )
    h_id, a_id = float(ids.iloc[0, 0]), float(ids.iloc[0, 1])

    row = {
        "home_elo": home_elo, "away_elo": away_elo,
        "home_xg":  home_xg,  "away_xg":  away_xg,
        "home_team_id": h_id, "away_team_id": a_id,
        "home_roll_ppg":     h["roll_ppg"],
        "away_roll_ppg":     a["roll_ppg"],
        "home_roll_xg_for":  h["roll_xg_for"],
        "away_roll_xg_for":  a["roll_xg_for"],
        "home_roll_xg_ag":   h["roll_xg_ag"],
        "away_roll_xg_ag":   a["roll_xg_ag"],
        "home_roll_gd":      h["roll_gd"],
        "away_roll_gd":      a["roll_gd"],
        "home_form_slope":   h["form_slope"],
        "away_form_slope":   a["form_slope"],
        "elo_delta":    home_elo - away_elo,
        "xg_delta":     home_xg  - away_xg,
        "ppg_delta":    h["roll_ppg"]    - a["roll_ppg"],
        "xg_for_delta": h["roll_xg_for"] - a["roll_xg_for"],
        "xg_ag_delta":  h["roll_xg_ag"]  - a["roll_xg_ag"],
        "gd_delta":     h["roll_gd"]     - a["roll_gd"],
        "slope_delta":  h["form_slope"]  - a["form_slope"],
    }

    X_new  = pd.DataFrame([row])[pipeline.feature_cols]
    proba  = pipeline.clf.predict_proba(X_new)[0]
    label  = int(np.argmax(proba))

    return {
        "home_team":       home_team,
        "away_team":       away_team,
        "predicted_label": OUTCOME_LABELS[label],
        "probabilities": {
            "draw":     round(float(proba[0]), 4),
            "home_win": round(float(proba[1]), 4),
            "away_win": round(float(proba[2]), 4),
        },
        "confidence":    round(float(proba[label]), 4),
        "_raw_proba":    proba.tolist(),
    }


# ===========================================================================
# §10  DROP-IN ENGINE (matches rf_model.py API)
# ===========================================================================

class XGBPredictionEngine:
    """Drop-in replacement for RandomForestModel in rf_model.py."""

    def __init__(self, data_path: str, window: int = FORM_WINDOW,
                 n_splits: int = N_SPLITS) -> None:
        self.window   = window
        self.pipeline = None
        if os.path.exists(data_path):
            ext    = os.path.splitext(data_path)[1].lower()
            df_raw = (load_json_matches(data_path) if ext == ".json"
                      else load_csv_matches(data_path))
            self._fit(df_raw)

    def _fit(self, df_raw: pd.DataFrame) -> None:
        df = encode_outcome(df_raw)
        df, feature_cols = build_features(df, self.window)
        self.pipeline, _ = train_final_model(df, feature_cols)
        print("[XGBPredictionEngine] Model trained and calibrated.")

    def predict(self, home_team, away_team,
                home_injured=False, away_injured=False):
        if self.pipeline is None:
            return None

        def _latest_ppg(team):
            df_tr = self.pipeline.df_train
            mask  = (df_tr["home_team"] == team) | (df_tr["away_team"] == team)
            rows  = df_tr[mask]
            if rows.empty:
                return 1.5
            zeros   = pd.Series(1.5, index=rows.index)
            is_home = rows["home_team"] == team
            ppg     = np.where(is_home, rows.get("home_roll_ppg", zeros),
                                        rows.get("away_roll_ppg", zeros))
            return float(np.nanmean(ppg))

        h_ppg = _latest_ppg(home_team) * (0.85 if home_injured else 1.0)
        a_ppg = _latest_ppg(away_team) * (0.85 if away_injured else 1.0)

        result = predict_match(
            self.pipeline, home_team, away_team,
            home_ppg_override=h_ppg if home_injured else None,
            away_ppg_override=a_ppg if away_injured else None,
        )
        p = result["probabilities"]
        return {
            "home_win": round(p["home_win"] * 100, 1),
            "draw":     round(p["draw"]     * 100, 1),
            "away_win": round(p["away_win"] * 100, 1),
        }


# ===========================================================================
# §11  MAIN
# ===========================================================================

def main(csv_path=None, json_path=None, window=FORM_WINDOW, n_splits=N_SPLITS):
    print("\n" + "=" * 56)
    print("  FOOTBALL MATCH PREDICTOR — XGBoost Pipeline")
    print("=" * 56)

    if csv_path and os.path.exists(csv_path):
        print(f"[INFO] Loading CSV: {csv_path}")
        df_raw = load_csv_matches(csv_path)
    elif json_path and os.path.exists(json_path):
        print(f"[INFO] Loading JSON: {json_path}")
        df_raw = load_json_matches(json_path)
    else:
        print("[INFO] No data file provided -> using synthetic dataset")
        df_raw = generate_synthetic_data(n_teams=12, seasons=4)

    print(f"[INFO] Matches loaded: {len(df_raw)}")
    print(f"[INFO] Date range: {df_raw['date'].min().date()} -> "
          f"{df_raw['date'].max().date()}")

    df = encode_outcome(df_raw)
    print(f"[INFO] Outcome distribution:\n"
          f"       Draw={(df['outcome']==0).mean():.1%}  "
          f"HomeWin={(df['outcome']==1).mean():.1%}  "
          f"AwayWin={(df['outcome']==2).mean():.1%}")

    print(f"\n[INFO] Building features (rolling window = {window})...")
    df, feature_cols = build_features(df, window)

    X = df[feature_cols]
    y = df["outcome"].values
    cross_validate_model(X, y, n_splits=n_splits)

    print("\n[INFO] Training final calibrated model...")
    pipeline, _ = train_final_model(df, feature_cols, window=window)

    teams = df_raw["home_team"].unique()
    if len(teams) >= 2:
        home_t, away_t = teams[0], teams[1]
        pred = predict_match(pipeline, home_t, away_t,
                              home_elo=1600, away_elo=1550)
        print(f"\n{'='*56}")
        print(f"  DEMO PREDICTION: {home_t} vs {away_t}")
        print(f"{'='*56}")
        print(f"  Prediction   : {pred['predicted_label']}")
        print(f"  Draw         : {pred['probabilities']['draw']:.2%}")
        print(f"  Home Win     : {pred['probabilities']['home_win']:.2%}")
        print(f"  Away Win     : {pred['probabilities']['away_win']:.2%}")
        print(f"  Confidence   : {pred['confidence']:.2%}")

    return pipeline


# ===========================================================================
# §12  CLI
# ===========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Football XGBoost Predictor")
    parser.add_argument("--csv",    default=None, help="Path to CSV file")
    parser.add_argument("--json",   default=None, help="Path to JSON file")
    parser.add_argument("--window", type=int, default=FORM_WINDOW)
    parser.add_argument("--splits", type=int, default=N_SPLITS)
    args = parser.parse_args()

    main(csv_path=args.csv, json_path=args.json,
         window=args.window, n_splits=args.splits)
