"""Stacking ensemble: Dixon-Coles + XGBoost + LightGBM + Random Forest -> calibrated meta-learner.

Class order everywhere: 0 = draw, 1 = home win, 2 = away win.

Training protocol (no temporal leakage):
1. Features are built by replaying history (features.py).
2. Walk-forward folds: every base model (including Dixon-Coles, refitted at the fold cutoff)
   is trained on the past only and predicts the next block -> out-of-fold (OOF) probabilities.
3. Meta-learner candidates (multinomial logistic regression, equal-weight average) are compared by
   a second walk-forward pass over the OOF block; the best by RPS wins.
4. A temperature is fitted on the meta-learner's own walk-forward predictions (calibration).
5. Final base models are refitted on all data.

Changes vs. the old pipeline: no balanced class weights (they inflate draw probabilities and
break calibration -- and the RF was being double-weighted), Poisson inputs no longer have
home/away swapped, Elo is real, and the meta-learner sees the same features at train and serve time.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from scipy.optimize import minimize_scalar
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

from . import poisson as pm
from .features import FEATURES, FeatureState, build_training_frame

log = logging.getLogger("ensemble")

BURN_IN = 380          # first season only seeds the feature state / Elo
N_FOLDS = 6
MIN_TRAIN = 300


def rps(y: np.ndarray, p: np.ndarray) -> float:
    """Ranked probability score over ordered outcomes (away, draw, home)."""
    order = p[:, [2, 0, 1]]
    onehot = np.eye(3)[y][:, [2, 0, 1]]
    return float(np.mean(np.sum((np.cumsum(order, 1) - np.cumsum(onehot, 1)) ** 2, 1) / 2))


def log_loss(y: np.ndarray, p: np.ndarray) -> float:
    return float(-np.mean(np.log(np.clip(p[np.arange(len(y)), y], 1e-12, 1))))


def brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean(np.sum((p - np.eye(3)[y]) ** 2, 1)))


def metric_row(name: str, y: np.ndarray, p: np.ndarray) -> dict:
    return {"model": name, "accuracy": float(np.mean(p.argmax(1) == y)), "log_loss": log_loss(y, p),
            "rps": rps(y, p), "brier": brier(y, p), "n": int(len(y))}


def walk_forward(n: int, n_splits: int, min_train: int):
    if n <= min_train:
        return
    size = (n - min_train) // n_splits
    for i in range(n_splits):
        start = min_train + i * size
        end = n if i == n_splits - 1 else start + size
        yield np.arange(start), np.arange(start, end)


def _apply_temperature(p: np.ndarray, t: float) -> np.ndarray:
    z = np.log(np.clip(p, 1e-12, 1)) / t
    z = np.exp(z - z.max(1, keepdims=True))
    return z / z.sum(1, keepdims=True)


def _fit_blend_weights(P: np.ndarray, y: np.ndarray, n_models: int) -> np.ndarray:
    """Convex weights over base-model probability vectors, fitted by log loss (softmax-parametrised)."""
    from scipy.optimize import minimize

    stacked = P.reshape(len(y), n_models, 3)

    def loss(z):
        w = np.exp(z - z.max())
        w /= w.sum()
        return log_loss(y, np.einsum("m,nmk->nk", w, stacked)) + 1e-3 * np.sum(z ** 2)

    z = minimize(loss, np.zeros(n_models), method="L-BFGS-B").x
    w = np.exp(z - z.max())
    return w / w.sum()


def _blend(P: np.ndarray, w: np.ndarray) -> np.ndarray:
    return np.einsum("m,nmk->nk", w, P.reshape(len(P), len(w), 3))


def _base_models():
    return {
        "xgboost": XGBClassifier(n_estimators=150, max_depth=2, learning_rate=0.03, subsample=0.8,
                                 colsample_bytree=0.8, min_child_weight=10, reg_lambda=5.0,
                                 eval_metric="mlogloss", n_jobs=2, random_state=42, verbosity=0),
        "lightgbm": LGBMClassifier(n_estimators=150, num_leaves=4, learning_rate=0.03, subsample=0.8,
                                   subsample_freq=1, colsample_bytree=0.8, min_child_samples=40,
                                   reg_lambda=5.0, n_jobs=2, random_state=42, verbose=-1),
        "random_forest": RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=20,
                                                max_features="sqrt", n_jobs=2, random_state=42),
    }


BASE_ORDER = ["xgboost", "lightgbm", "random_forest", "poisson"]


@dataclass
class EnsembleModel:
    data_version: str = ""
    half_life: float = pm.DEFAULT_HALF_LIFE
    base: dict = field(default_factory=dict)
    poisson: pm.DixonColes | None = None
    meta: object = None
    meta_kind: str = "logistic"
    blend_weights: np.ndarray | None = None
    temperature: float = 1.0
    state: FeatureState | None = None
    last_date: pd.Timestamp | None = None
    metrics: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ training
    def train(self, df: pd.DataFrame, data_version: str = "", half_life: float | None = None) -> "EnsembleModel":
        t0 = time.time()
        df = df.sort_values(["date", "id"]).reset_index(drop=True)
        self.data_version = data_version
        if half_life:
            self.half_life = half_life
        feats, state = build_training_frame(df)
        X_all, y_all = feats[FEATURES].to_numpy(float), feats["outcome"].to_numpy(int)

        # Rows after burn-in are the supervised set; burn-in matches still feed the Poisson fits.
        start = min(BURN_IN, len(df) // 3)
        X, y = X_all[start:], y_all[start:]
        dates = df["date"].iloc[start:].reset_index(drop=True)

        oof = np.full((len(X), 3 * len(BASE_ORDER)), np.nan)
        folds = list(walk_forward(len(X), N_FOLDS, MIN_TRAIN))
        for tr, va in folds:
            models = _base_models()
            for k, (name, mdl) in enumerate(models.items()):
                mdl.fit(X[tr], y[tr])
                oof[va, 3 * k:3 * k + 3] = mdl.predict_proba(X[va])
            cutoff = dates.iloc[va[0]]
            dc = pm.DixonColes(self.half_life).fit_df(df[df["date"] < cutoff], as_of=cutoff)
            sub = df.iloc[start + va]
            oof[va, 9:12] = np.array([dc.predict_1x2(h, a) for h, a in zip(sub["homeTeam"], sub["awayTeam"])])

        mask = ~np.isnan(oof).any(1)
        P, yo = oof[mask], y[mask]
        ctx = X[mask][:, [FEATURES.index("elo_diff")]] / 400.0
        meta_X = np.hstack([P, ctx])

        # ---- choose meta learner by a second walk-forward over the OOF block
        meta_preds = {"logistic": [], "weighted_blend": [], "average": []}
        meta_y = []
        for tr, va in walk_forward(len(yo), 4, max(120, len(yo) // 3)):
            lr = LogisticRegression(C=0.5, max_iter=2000).fit(meta_X[tr], yo[tr])
            meta_preds["logistic"].append(lr.predict_proba(meta_X[va]))
            meta_preds["average"].append(P[va].reshape(len(va), len(BASE_ORDER), 3).mean(1))
            w = _fit_blend_weights(P[tr], yo[tr], len(BASE_ORDER))
            meta_preds["weighted_blend"].append(_blend(P[va], w))
            meta_y.append(yo[va])
        my = np.concatenate(meta_y)
        scores = {k: rps(my, np.vstack(v)) for k, v in meta_preds.items()}
        self.meta_kind = min(scores, key=scores.get)
        best_oof = np.vstack(meta_preds[self.meta_kind])

        # ---- temperature calibration on the meta learner's out-of-sample predictions
        res = minimize_scalar(lambda t: log_loss(my, _apply_temperature(best_oof, t)), bounds=(0.5, 2.5), method="bounded")
        self.temperature = float(res.x)
        calibrated = _apply_temperature(best_oof, self.temperature)

        if self.meta_kind == "logistic":
            self.meta = LogisticRegression(C=0.5, max_iter=2000).fit(meta_X, yo)
        self.blend_weights = _fit_blend_weights(P, yo, len(BASE_ORDER))

        # ---- metrics on the common evaluation window (last part of OOF)
        n_eval = len(my)
        tail = slice(len(yo) - n_eval, len(yo))
        freq = np.bincount(y[: len(y) - n_eval], minlength=3) / max(1, len(y) - n_eval)
        rows = [metric_row("Baseline (class frequency)", my, np.tile(freq, (n_eval, 1)))]
        labels = {"xgboost": "XGBoost", "lightgbm": "LightGBM", "random_forest": "Random Forest", "poisson": "Dixon-Coles Poisson"}
        for k, name in enumerate(BASE_ORDER):
            rows.append(metric_row(labels[name], my, P[tail, 3 * k:3 * k + 3]))
        rows.append(metric_row(f"Stacked ensemble ({self.meta_kind})", my, calibrated))

        # reliability curve: pool all three outcomes
        flat_p = calibrated.ravel()
        flat_y = np.eye(3)[my].ravel()
        bins = np.linspace(0, 1, 11)
        calib = []
        for lo, hi in zip(bins[:-1], bins[1:]):
            sel = (flat_p >= lo) & (flat_p < hi)
            if sel.sum() >= 5:
                calib.append({"bin": f"{lo:.1f}-{hi:.1f}", "predicted": float(flat_p[sel].mean()),
                              "observed": float(flat_y[sel].mean()), "count": int(sel.sum())})

        # ---- final fit on everything
        self.base = _base_models()
        for mdl in self.base.values():
            mdl.fit(X, y)
        self.poisson = pm.DixonColes(self.half_life).fit_df(df)
        self.state = state
        self.last_date = df["date"].max()

        imp = np.zeros(len(FEATURES))
        for name in ("xgboost", "lightgbm", "random_forest"):
            fi = np.asarray(self.base[name].feature_importances_, float)
            imp += fi / fi.sum() if fi.sum() else 0
        imp /= 3
        conf = calibrated.max(1)
        self.metrics = {
            "trained_at": pd.Timestamp.utcnow().isoformat(),
            "training_seconds": round(time.time() - t0, 1),
            "matches": int(len(df)), "supervised_rows": int(len(y)), "evaluation_rows": int(n_eval),
            "seasons": sorted(int(s) for s in df["season"].unique()) if "season" in df else [],
            "meta_learner": self.meta_kind, "meta_candidates_rps": scores,
            "blend_weights": {k: float(v) for k, v in zip(BASE_ORDER, self.blend_weights)},
            "temperature": self.temperature, "half_life_days": self.half_life,
            "models": rows, "calibration": calib,
            "feature_importance": sorted(
                [{"feature": f, "importance": float(v)} for f, v in zip(FEATURES, imp)],
                key=lambda r: -r["importance"]),
            "confidence_buckets": [
                {"bucket": label, "count": int(sel.sum()),
                 "accuracy": float(np.mean(calibrated[sel].argmax(1) == my[sel])) if sel.sum() else None}
                for label, sel in (("<45%", conf < 0.45), ("45-55%", (conf >= 0.45) & (conf < 0.55)),
                                   ("55-65%", (conf >= 0.55) & (conf < 0.65)), (">=65%", conf >= 0.65))],
            "outcome_distribution": {"draw": float(np.mean(y == 0)), "home": float(np.mean(y == 1)), "away": float(np.mean(y == 2))},
            "poisson": {"home_advantage": float(np.exp(self.poisson.home_adv)), "rho": self.poisson.rho},
        }
        log.info("Ensemble trained in %.1fs (meta=%s, T=%.2f)", time.time() - t0, self.meta_kind, self.temperature)
        return self

    # ------------------------------------------------------------------ inference
    def base_probs(self, home: str, away: str) -> tuple[dict, np.ndarray]:
        date = self.last_date + pd.Timedelta(days=7)
        row = self.state.row(home, away, date)
        x = np.array([[row[f] for f in FEATURES]], float)
        out = {name: self.base[name].predict_proba(x)[0] for name in ("xgboost", "lightgbm", "random_forest")}
        out["poisson"] = self.poisson.predict_1x2(home, away)
        return out | {"_features": row}, x

    def predict(self, home: str, away: str, lam_mult: float = 1.0, mu_mult: float = 1.0) -> dict:
        probs, x = self.base_probs(home, away)
        feats = probs.pop("_features")
        P = np.hstack([probs[k] for k in BASE_ORDER])[None, :]
        if self.meta_kind == "logistic":
            meta_in = np.hstack([P, x[:, [FEATURES.index("elo_diff")]] / 400.0])
            p = self.meta.predict_proba(meta_in)
        elif self.meta_kind == "weighted_blend":
            p = _blend(P, self.blend_weights)
        else:
            p = P.reshape(1, len(BASE_ORDER), 3).mean(1)
        p = _apply_temperature(p, self.temperature)[0]
        ens = {"draw": float(p[0]), "home_win": float(p[1]), "away_win": float(p[2])}

        base_matrix = self.poisson.matrix(home, away)
        adj_matrix = self.poisson.matrix(home, away, lam_mult, mu_mult)
        final = ens
        if lam_mult != 1.0 or mu_mult != 1.0:
            # Propagate the availability adjustment through the ensemble via the Poisson likelihood ratio.
            b, a = pm.outcome_probs(base_matrix), pm.outcome_probs(adj_matrix)
            raw = {k: ens[k] * a[k] / max(b[k], 1e-9) for k in ens}
            s = sum(raw.values())
            final = {k: v / s for k, v in raw.items()}
        matrix = pm.reweight_to_outcomes(adj_matrix, final)
        lam, mu = self.poisson.expected_goals(home, away)
        return {
            "ensemble": final, "ensemble_unadjusted": ens,
            "base": {k: {"draw": float(v[0]), "home_win": float(v[1]), "away_win": float(v[2])} for k, v in probs.items()},
            "matrix": matrix, "features": feats,
            "xg": {"home": lam * lam_mult, "away": mu * mu_mult, "home_base": lam, "away_base": mu},
        }
