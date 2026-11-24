"""Train and persist the ensemble.  Usage (from backend/):  python -m app.ml.train [--sweep]"""
from __future__ import annotations

import argparse
import json
import logging

import numpy as np
import pandas as pd

from .. import config
from ..services.data_store import DataStore
from . import poisson as pm
from .ensemble import EnsembleModel, rps, walk_forward

MODEL_PATH = config.MODELS_DIR / "ensemble.joblib"
METRICS_PATH = config.MODELS_DIR / "metrics.json"


def sweep_half_life(df: pd.DataFrame, candidates=(90, 180, 270, 365)) -> tuple[float, list[dict]]:
    """Walk-forward RPS of Dixon-Coles alone for each half-life; returns the best and the table."""
    df = df.sort_values(["date", "id"]).reset_index(drop=True)
    y = np.where(df.homeScore > df.awayScore, 1, np.where(df.homeScore < df.awayScore, 2, 0))
    folds = list(walk_forward(len(df), 8, 380))
    table = []
    for hl in candidates:
        preds, ys = [], []
        for tr, va in folds:
            cutoff = df["date"].iloc[va[0]]
            dc = pm.DixonColes(hl).fit_df(df.iloc[tr], as_of=cutoff)
            preds.append(np.array([dc.predict_1x2(h, a) for h, a in zip(df.homeTeam.iloc[va], df.awayTeam.iloc[va])]))
            ys.append(y[va])
        table.append({"half_life": hl, "rps": rps(np.concatenate(ys), np.vstack(preds))})
    best = min(table, key=lambda r: r["rps"])["half_life"]
    return float(best), table


def train_and_save(store: DataStore | None = None, sweep: bool = False) -> EnsembleModel:
    import joblib

    store = store or DataStore()
    df = store.matches_df
    if df.empty:
        raise RuntimeError("No match data found in data/snapshot/matches.json")
    half_life, table = (sweep_half_life(df) if sweep else (pm.DEFAULT_HALF_LIFE, []))
    model = EnsembleModel().train(df, data_version=store.version, half_life=half_life)
    if table:
        model.metrics["half_life_sweep"] = table
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH, compress=3)
    METRICS_PATH.write_text(json.dumps(model.metrics, indent=2))
    return model


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true", help="validate the Dixon-Coles half-life first")
    args = ap.parse_args()
    m = train_and_save(sweep=args.sweep)
    print(json.dumps({k: m.metrics[k] for k in ("matches", "meta_learner", "temperature", "half_life_days", "training_seconds")}, indent=2))
    if "half_life_sweep" in m.metrics:
        for r in m.metrics["half_life_sweep"]:
            print(f"  half_life={r['half_life']:>5}  rps={r['rps']:.4f}")
    print(f"{'model':<34} {'acc':>6} {'logloss':>8} {'rps':>7} {'brier':>7}")
    for r in m.metrics["models"]:
        print(f"{r['model']:<34} {r['accuracy']:>6.3f} {r['log_loss']:>8.4f} {r['rps']:>7.4f} {r['brier']:>7.4f}")
