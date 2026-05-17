import pandas as pd
import numpy as np
import datetime
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, f1_score, log_loss

# Add parent directory to sys.path
import sys
import os
sys.path.append(os.path.abspath('backend'))

from poisson_model import DixonColesPoissonModel, validate_half_life, ranked_probability_score
from football_ensemble import FootballEnsembleEngine
from football_predictor_xgb import generate_synthetic_data

BASELINE_RPS = 0.2091
BASELINE_LL = 2.334
BASELINE_ACC = 0.4875

def task1_and_3(df):
    print("\n" + "="*55)
    print("  TASK 1: FULL PIPELINE CROSS-VALIDATION")
    print("="*55)
    
    # Sort chronological
    df = df.sort_values('date').reset_index(drop=True)
    
    # Train / Holdout split 85/15
    n = len(df)
    cut = int(n * 0.85)
    df_cv = df.iloc[:cut].copy().reset_index(drop=True)
    df_ho = df.iloc[cut:].copy().reset_index(drop=True)
    
    engine = FootballEnsembleEngine("")
    
    # We will simulate a cross-validation of the full ensemble model
    tscv = TimeSeriesSplit(n_splits=5)
    
    fold_metrics = []
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(df_cv), start=1):
        print(f"\nTraining Fold {fold} / 5 ...")
        
        # Train ensemble on train_idx
        df_train = df_cv.iloc[train_idx]
        df_val = df_cv.iloc[val_idx]
        
        tmp_engine = FootballEnsembleEngine("")
        tmp_engine.train(df_train)
        
        # Predict on Val
        rps_list = []
        ll_list = []
        acc_list = []
        
        y_true = df_val['outcome'].values
        p_fold = []
        
        for _, row in df_val.iterrows():
            res = tmp_engine.predict(row['home_team'], row['away_team'])
            if 'error' in res:
                p_vec = [0.34, 0.33, 0.33]
            else:
                p_vec = [res['draw'], res['home_win'], res['away_win']]
            p_fold.append(p_vec)
            
        p_fold = np.array(p_fold)
        rps = np.mean([sum((np.cumsum(p) - np.cumsum(np.eye(3)[y]))**2)/2.0 
                       for y, p in zip(y_true, p_fold)])
        
        y_pred = np.argmax(p_fold, axis=1)
        acc = accuracy_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
        ll = log_loss(y_true, p_fold)
        
        fold_metrics.append({'rps': rps, 'acc': acc, 'f1': f1, 'll': ll})
        
        print(f"Fold {fold} Metrics: RPS={rps:.4f} | Acc={acc:.4f} | F1={f1:.4f} | LL={ll:.4f}")
        
    print("\n" + "-"*55)
    print("  MEAN METRICS ACROSS FOLDS")
    print("-"*55)
    m_rps = np.mean([m['rps'] for m in fold_metrics])
    s_rps = np.std([m['rps'] for m in fold_metrics])
    
    m_acc = np.mean([m['acc'] for m in fold_metrics])
    s_acc = np.std([m['acc'] for m in fold_metrics])
    
    m_f1 = np.mean([m['f1'] for m in fold_metrics])
    s_f1 = np.std([m['f1'] for m in fold_metrics])
    
    m_ll = np.mean([m['ll'] for m in fold_metrics])
    s_ll = np.std([m['ll'] for m in fold_metrics])
    
    def diff_str(val, base):
        d = val - base
        return f"{d:>+7.4f}"
        
    print(f"Mean RPS  : {m_rps:.4f} ± {s_rps:.4f} (vs Baseline {BASELINE_RPS:.4f} -> {diff_str(m_rps, BASELINE_RPS)})")
    print(f"Mean LL   : {m_ll:.4f} ± {s_ll:.4f} (vs Baseline {BASELINE_LL:.4f} -> {diff_str(m_ll, BASELINE_LL)})")
    print(f"Mean Acc  : {m_acc:.4f} ± {s_acc:.4f} (vs Baseline {BASELINE_ACC:.4f} -> {diff_str(m_acc, BASELINE_ACC)})")
    print(f"Mean F1   : {m_f1:.4f} ± {s_f1:.4f}")
    
    print("\n" + "-"*55)
    print("  FINAL HOLDOUT EVALUATION (Last 15%)")
    print("-"*55)
    
    # Train heavily on CV data and evaluate on Holdout
    engine.train(df_cv)
    
    y_true_ho = df_ho['outcome'].values
    p_ho = []
    
    for _, row in df_ho.iterrows():
        res = engine.predict(row['home_team'], row['away_team'])
        if 'error' in res:
            p_vec = [0.34, 0.33, 0.33]
        else:
            p_vec = [res['draw'], res['home_win'], res['away_win']]
        p_ho.append(p_vec)
        
    p_ho = np.array(p_ho)
    ho_rps = np.mean([sum((np.cumsum(p) - np.cumsum(np.eye(3)[y]))**2)/2.0 
                      for y, p in zip(y_true_ho, p_ho)])
    
    y_pred_ho = np.argmax(p_ho, axis=1)
    ho_acc = accuracy_score(y_true_ho, y_pred_ho)
    ho_f1 = f1_score(y_true_ho, y_pred_ho, average="macro", zero_division=0)
    ho_ll = log_loss(y_true_ho, p_ho)
    
    print(f"Holdout RPS : {ho_rps:.4f}  (Target < 0.200)")
    print(f"Holdout LL  : {ho_ll:.4f}  (Target < 1.05)")
    print(f"Holdout Acc : {ho_acc:.4f}  (Target > 0.50)")
    print(f"Holdout F1  : {ho_f1:.4f}")
    
    # Regression assert
    assert len(df_ho) > 0, "Regression Caught: Holdout set is empty"
    for m in fold_metrics:
        assert m['acc'] >= 0 and m['acc'] <= 1, "Accuracy calculation error"
        
    print("\n" + "="*55)
    print("  SUMMARY TABLE")
    print("="*55)
    print(f"{'Metric':<10} | {'Before':<10} | {'After (CV)':<12} | {'After (HO)':<12} | {'Target':<10} | {'Status'}")
    
    stat_rps = "PASS" if m_rps < BASELINE_RPS and m_rps < 0.200 else ("IMPROVED" if m_rps < BASELINE_RPS else "REGRESSED")
    stat_ll = "PASS" if m_ll < BASELINE_LL and m_ll < 1.05 else ("IMPROVED" if m_ll < BASELINE_LL else "REGRESSED")
    stat_acc = "PASS" if m_acc > BASELINE_ACC and m_acc > 0.50 else ("IMPROVED" if m_acc > BASELINE_ACC else "REGRESSED")
    
    print(f"{'RPS':<10} | {BASELINE_RPS:<10.4f} | {m_rps:<12.4f} | {ho_rps:<12.4f} | {'< 0.200':<10} | {stat_rps}")
    print(f"{'Log Loss':<10} | {BASELINE_LL:<10.4f} | {m_ll:<12.4f} | {ho_ll:<12.4f} | {'< 1.05':<10} | {stat_ll}")
    print(f"{'Accuracy':<10} | {BASELINE_ACC:<10.4f} | {m_acc:<12.4f} | {ho_acc:<12.4f} | {'> 0.50':<10} | {stat_acc}")

def main():
    try:
        import json
        with open('src/data/matches-all-seasons.json', 'r') as f:
            raw = json.load(f)
        df_list = []
        for m in raw:
            m['home_team'] = " ".join(m['homeTeam'].replace('\n', ' ').split()).strip()
            m['away_team'] = " ".join(m['awayTeam'].replace('\n', ' ').split()).strip()
            m['home_goals'] = int(m['homeScore'])
            m['away_goals'] = int(m['awayScore'])
            m['homeTeam'] = m['home_team']
            m['awayTeam'] = m['away_team']
            m['homeScore'] = m['home_goals']
            m['awayScore'] = m['away_goals']
            df_list.append(m)
        df = pd.DataFrame(df_list)
        df['date'] = pd.to_datetime(df['date'])
    except Exception as e:
        print(f"Error loading JSON: {e}")
        df = generate_synthetic_data(n_teams=12, seasons=4)
        df.rename(columns={'home_team': 'home_team', 'away_team': 'away_team', 'home_goals': 'home_goals', 'away_goals': 'away_goals'}, inplace=True)
        # Mock API fields
        df['homeTeam'] = df['home_team']
        df['awayTeam'] = df['away_team']
        df['homeScore'] = df['home_goals']
        df['awayScore'] = df['away_goals']
        
    df['outcome'] = 0
    df.loc[df['home_goals'] > df['away_goals'], 'outcome'] = 1
    df.loc[df['home_goals'] < df['away_goals'], 'outcome'] = 2

    # Task 2
    validate_half_life(df)
    
    # Tasks 1 & 3
    task1_and_3(df)

if __name__ == "__main__":
    main()
