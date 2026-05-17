import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')
from poisson_model import validate_half_life
from football_ensemble import FootballEnsembleEngine
from football_predictor_xgb import main as test_xgb

# Baseline (Before) Metrics
before_metrics = {
    "rps": 0.2091,
    "cv_ll": 2.5898,
    "ho_ll": 1.3766,
    "cv_acc": 0.4111,
    "ho_acc": 0.4825,
    "draw_recall": 0.1429 # Fold 5 proxy
}

print("--- TASK 2: DIXON-COLES SWEEP ---")
df = pd.read_json('../src/data/matches-all-seasons.json')
df.rename(columns={'homeTeam':'home_team', 'awayTeam':'away_team', 'homeScore':'home_goals', 'awayScore':'away_goals'}, inplace=True)
best_hl = validate_half_life(df)

print("\n--- TASK 3: META-LEARNER BENCHMARK ---")
df2 = pd.read_json('../src/data/matches-all-seasons.json')
engine = FootballEnsembleEngine("../src/data/matches-all-seasons.json")
engine.train(df2)

print("\n--- TASK 1: FULL CV RESULTS ---")
# main returns a dict with 'cv' and 'ho' objects
results = test_xgb(json_path='../src/data/matches-all-seasons.json', window=5, n_splits=5)

# Extract metrics for table
after_metrics = {
    "rps": results['cv'].mean_rps,
    "cv_ll": results['cv'].mean_log_loss,
    "ho_ll": results['ho']['log_loss'],
    "cv_acc": results['cv'].mean_acc,
    "ho_acc": results['ho']['acc'],
    "draw_recall": results['cv'].mean_draw_recall
}

targets = {
    "rps": 0.200,
    "cv_ll": 1.2,
    "ho_ll": 1.05,
    "cv_acc": 0.50,
    "ho_acc": 0.50,
    "draw_recall": 0.30
}

def get_status(metric, val, target):
    if metric in ["rps", "cv_ll", "ho_ll"]:
        return "PASS" if val < target else "FAIL"
    return "PASS" if val > target else "FAIL"

print("\n" + "="*65)
print(f"{'Metric':<15} | {'Before':<10} | {'After':<10} | {'Target':<10} | {'Status':<8}")
print("-" * 65)
for m in ["rps", "cv_ll", "ho_ll", "cv_acc", "ho_acc", "draw_recall"]:
    b = before_metrics[m]
    a = after_metrics[m]
    t = targets[m]
    status = get_status(m, a, t)
    print(f"{m:<15} | {b:<10.4f} | {a:<10.4f} | {t:<10.4f} | {status:<8}")
print("="*65)
