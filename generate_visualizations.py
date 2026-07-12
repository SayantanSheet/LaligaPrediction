import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from sklearn.metrics import (
    accuracy_score, log_loss, confusion_matrix, roc_curve, auc
)
from sklearn.calibration import calibration_curve
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.linear_model import LogisticRegression

# Set paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(PROJECT_ROOT, 'backend'))

from poisson_model import DixonColesPoissonModel
from football_ensemble import FootballEnsembleEngine, walk_forward_split
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier

# Set print/plot styles
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.edgecolor'] = '#CCCCCC'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#EEEEEE'
plt.rcParams['grid.linewidth'] = 0.5

# Directory where artifacts should go
ARTIFACTS_DIR = "/home/sayantan/.gemini/antigravity/brain/b5bef958-8828-47f8-bcf3-b0a97d6f637f"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# Helper function to compute Ranked Probability Score (RPS)
def ranked_probability_score(y_true, y_proba):
    # y_true is 0 (Draw), 1 (Home Win), 2 (Away Win)
    # y_proba is N x 3
    N = len(y_true)
    rps_list = []
    for i in range(N):
        oh = np.zeros(3)
        oh[int(y_true[i])] = 1.0
        cum_pred = np.cumsum(y_proba[i])
        cum_true = np.cumsum(oh)
        rps_list.append(np.sum((cum_pred - cum_true) ** 2) / 2.0)
    return np.mean(rps_list)

def draw_overall_pipeline():
    print("[INFO] Generating Overall Prediction Pipeline Diagram...")
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.axis('off')
    
    # Define style helpers
    box_blue = dict(boxstyle="round,pad=0.5", facecolor="#EFF6FF", edgecolor="#2563EB", linewidth=1.5)
    box_amber = dict(boxstyle="round,pad=0.5", facecolor="#FFFBEB", edgecolor="#D97706", linewidth=1.5)
    box_green = dict(boxstyle="round,pad=0.5", facecolor="#F0FDF4", edgecolor="#16A34A", linewidth=1.5)
    box_red = dict(boxstyle="round,pad=0.5", facecolor="#FEF2F2", edgecolor="#DC2626", linewidth=1.5)
    
    # 1. Inputs
    ax.text(0.12, 0.85, "Matches JSON Database\n(Historical & Live Scraped)", ha="center", va="center", bbox=box_blue, fontsize=9)
    ax.text(0.12, 0.55, "Injury Matrix API\n(Key Player Penalties)", ha="center", va="center", bbox=box_blue, fontsize=9)
    ax.text(0.12, 0.25, "Team Elo System\n(Live Ratings)", ha="center", va="center", bbox=box_blue, fontsize=9)
    
    # Arrows from Inputs to Feature Engineering
    ax.annotate("", xy=(0.28, 0.85), xytext=(0.20, 0.85), arrowprops=dict(arrowstyle="->", color="#4B5563", lw=1.5))
    ax.annotate("", xy=(0.28, 0.55), xytext=(0.20, 0.55), arrowprops=dict(arrowstyle="->", color="#4B5563", lw=1.5))
    ax.annotate("", xy=(0.28, 0.25), xytext=(0.20, 0.25), arrowprops=dict(arrowstyle="->", color="#4B5563", lw=1.5))
    
    # 2. Processing / Splitting
    ax.text(0.38, 0.55, "Zero-Leakage Data Engine\n\n- Rolling Stats (shift=1)\n- Walk-Forward Splitter\n- Ordinal Team Encoders", ha="center", va="center", bbox=box_amber, fontsize=9)
    
    # Arrows from Processing to Base Models
    ax.annotate("", xy=(0.48, 0.55), xytext=(0.53, 0.80), arrowprops=dict(arrowstyle="<-", color="#4B5563", lw=1.5))
    ax.annotate("", xy=(0.48, 0.55), xytext=(0.53, 0.60), arrowprops=dict(arrowstyle="<-", color="#4B5563", lw=1.5))
    ax.annotate("", xy=(0.48, 0.55), xytext=(0.53, 0.40), arrowprops=dict(arrowstyle="<-", color="#4B5563", lw=1.5))
    ax.annotate("", xy=(0.48, 0.55), xytext=(0.53, 0.20), arrowprops=dict(arrowstyle="<-", color="#4B5563", lw=1.5))
    
    # 3. Base Models
    ax.text(0.62, 0.80, "Poisson (Dixon-Coles)\n(Draw Inflated Team Strengths)", ha="center", va="center", bbox=box_green, fontsize=9)
    ax.text(0.62, 0.60, "Random Forest Classifier\n(Entropy based ensemble)", ha="center", va="center", bbox=box_green, fontsize=9)
    ax.text(0.62, 0.40, "XGBoost Classifier\n(Depth=4 Gradient Boosting)", ha="center", va="center", bbox=box_green, fontsize=9)
    ax.text(0.62, 0.20, "LightGBM Classifier\n(Leaf-wise Tree Growth)", ha="center", va="center", bbox=box_green, fontsize=9)
    
    # Arrows from Base Models to Meta-learner
    ax.annotate("", xy=(0.78, 0.50), xytext=(0.71, 0.80), arrowprops=dict(arrowstyle="->", color="#4B5563", lw=1.5))
    ax.annotate("", xy=(0.78, 0.50), xytext=(0.71, 0.60), arrowprops=dict(arrowstyle="->", color="#4B5563", lw=1.5))
    ax.annotate("", xy=(0.78, 0.50), xytext=(0.71, 0.40), arrowprops=dict(arrowstyle="->", color="#4B5563", lw=1.5))
    ax.annotate("", xy=(0.78, 0.50), xytext=(0.71, 0.20), arrowprops=dict(arrowstyle="->", color="#4B5563", lw=1.5))
    
    rect = patches.ConnectionPatch(xyA=(0.48, 0.45), xyB=(0.80, 0.45), coordsA="data", coordsB="data", 
                                  arrowstyle="->", color="#3B82F6", lw=1.5, linestyle="--")
    ax.add_artist(rect)
    ax.text(0.64, 0.48, "Elo & PPG Context", color="#2563EB", fontsize=8, ha="center")
    
    # 4. Meta Learner
    ax.text(0.85, 0.50, "XGBoost Meta-Learner\n(Calibrated depth=2)\nOR Logistic Regression", ha="center", va="center", bbox=box_red, fontsize=9)
    
    # Arrow from Meta Learner to output
    ax.annotate("", xy=(0.98, 0.50), xytext=(0.92, 0.50), arrowprops=dict(arrowstyle="->", color="#DC2626", lw=2))
    
    # Output outcome label
    ax.text(1.03, 0.50, "Probability Vector:\n[Draw, Home, Away]\n& Projected Score", ha="left", va="center", 
            bbox=dict(boxstyle="square,pad=0.3", facecolor="#FAFAFA", edgecolor="#111111", lw=1), fontsize=8)
    
    # Header Titles
    ax.text(0.12, 0.96, "1. DATA INPUTS", fontsize=11, fontweight="bold", ha="center", color="#1F2937")
    ax.text(0.38, 0.96, "2. ZERO-LEAKAGE PIPELINE", fontsize=11, fontweight="bold", ha="center", color="#1F2937")
    ax.text(0.62, 0.96, "3. BASE PREDICTORS", fontsize=11, fontweight="bold", ha="center", color="#1F2937")
    ax.text(0.85, 0.96, "4. META-LEARNER", fontsize=11, fontweight="bold", ha="center", color="#1F2937")
    ax.text(1.06, 0.96, "5. DECISION OUT", fontsize=11, fontweight="bold", ha="left", color="#1F2937")
    
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, "pipeline_diagram.png"), bbox_inches="tight")
    plt.close()
    print("[INFO] Overall Pipeline diagram saved.")


def evaluate_models():
    print("[INFO] Training and evaluating models...")
    # Load dataset
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
        m['home_elo'] = float(m.get('homeElo', 1500.0))
        m['away_elo'] = float(m.get('awayElo', 1500.0))
        df_list.append(m)
    df = pd.DataFrame(df_list)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    df['outcome'] = 0
    df.loc[df['home_goals'] > df['away_goals'], 'outcome'] = 1
    df.loc[df['home_goals'] < df['away_goals'], 'outcome'] = 2
    
    # Train / Holdout split 85/15
    n = len(df)
    cut = int(n * 0.85)
    df_cv = df.iloc[:cut].copy().reset_index(drop=True)
    df_ho = df.iloc[cut:].copy().reset_index(drop=True)
    
    engine = FootballEnsembleEngine("")
    
    df_cv_feats = engine._compute_rolling_features(engine._prepare_data(df_cv))
    poi_df_cv = df_cv[['home_team', 'away_team', 'home_goals', 'away_goals', 'date']].copy()
    
    X_data = df_cv_feats[[
        'home_roll_gs', 'home_roll_ga', 'home_ppg',
        'away_roll_gs', 'away_roll_ga', 'away_ppg'
    ]].copy()
    X_data['elo_difference'] = df_cv['home_elo'].values - df_cv['away_elo'].values
    y_data = df_cv['outcome'].values
    
    start_idx = len(df_cv) // 5
    X = X_data.iloc[start_idx:]
    y = y_data[start_idx:]
    
    tscv_iterator = list(walk_forward_split(X, n_splits=5, min_train_size=150))
    
    # Predictions storage
    oof_poi = np.zeros((len(X), 3))
    oof_rf = np.zeros((len(X), 3))
    oof_xgb = np.zeros((len(X), 3))
    oof_lgbm = np.zeros((len(X), 3))
    oof_ensemble = np.zeros((len(X), 3))
    
    for train_idx, val_idx in tscv_iterator:
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        sw = compute_sample_weight('balanced', y_train)
        
        # Fit Base models
        rf_tmp = RandomForestClassifier(n_estimators=500, max_features='sqrt', min_samples_leaf=5, class_weight='balanced', n_jobs=-1, random_state=42)
        rf_tmp.fit(X_train, y_train, sample_weight=sw)
        xgb_tmp = XGBClassifier(n_estimators=100, max_depth=4, random_state=42).fit(X_train, y_train, sample_weight=sw)
        lgbm_tmp = LGBMClassifier(n_estimators=100, max_depth=4, random_state=42, verbose=-1).fit(X_train, y_train, sample_weight=sw)
        
        cutoff_date = df_cv.iloc[start_idx + val_idx[0]]['date']
        poi_tmp = DixonColesPoissonModel().fit(poi_df_cv, prediction_date=cutoff_date)
        
        p_rf = rf_tmp.predict_proba(X_val)
        p_xgb = xgb_tmp.predict_proba(X_val)
        p_lgbm = lgbm_tmp.predict_proba(X_val)
        
        p_poi = []
        for idx in val_idx:
            row = df_cv.iloc[start_idx + idx]
            probs = poi_tmp.predict_proba(row['homeTeam'], row['awayTeam'])
            p_poi.append([probs['draw'], probs['home_win'], probs['away_win']])
        p_poi = np.array(p_poi)
        
        oof_rf[val_idx] = p_rf
        oof_xgb[val_idx] = p_xgb
        oof_lgbm[val_idx] = p_lgbm
        oof_poi[val_idx] = p_poi
        
        # Fit Meta-Learner on Meta-features for this fold (simulated walk-forward)
        # To avoid meta-model leakage, we can fit a meta XGBoost on train_idx of OOFs
        # Build meta-features for train and val
        stacked_train = np.hstack([oof_rf[train_idx], oof_xgb[train_idx], oof_lgbm[train_idx], oof_poi[train_idx]])
        context_train = df_cv_feats.loc[X.index[train_idx], ['home_ppg', 'away_ppg']].values
        elo_train = (df_cv.loc[X.index[train_idx], 'home_elo'] - df_cv.loc[X.index[train_idx], 'away_elo']).values.reshape(-1, 1)
        X_meta_train = np.hstack([stacked_train, context_train, elo_train])
        
        stacked_val = np.hstack([p_rf, p_xgb, p_lgbm, p_poi])
        context_val = df_cv_feats.loc[X.index[val_idx], ['home_ppg', 'away_ppg']].values
        elo_val = (df_cv.loc[X.index[val_idx], 'home_elo'] - df_cv.loc[X.index[val_idx], 'away_elo']).values.reshape(-1, 1)
        X_meta_val = np.hstack([stacked_val, context_val, elo_val])
        
        # Fit a meta-learner (LogisticRegression or XGBoost)
        sw_m = compute_sample_weight('balanced', y_train)
        meta_tmp = LogisticRegression(random_state=42, max_iter=1000)
        meta_tmp.fit(X_meta_train, y_train, sample_weight=sw_m)
        oof_ensemble[val_idx] = meta_tmp.predict_proba(X_meta_val)
        
    used_idx = np.where(np.any(oof_rf != 0, axis=1))[0]
    
    y_eval = y[used_idx]
    pred_poi = oof_poi[used_idx]
    pred_rf = oof_rf[used_idx]
    pred_xgb = oof_xgb[used_idx]
    pred_lgbm = oof_lgbm[used_idx]
    pred_ens = oof_ensemble[used_idx]
    
    models = ['Poisson', 'Random Forest', 'XGBoost', 'LightGBM', 'Stacking Ensemble']
    preds = [pred_poi, pred_rf, pred_xgb, pred_lgbm, pred_ens]
    
    acclist = [accuracy_score(y_eval, np.argmax(p, axis=1)) for p in preds]
    lllist = [log_loss(y_eval, p) for p in preds]
    rpslist = [ranked_probability_score(y_eval, p) for p in preds]
    
    print(f"Metrics evaluated on CV size: {len(y_eval)}")
    for m, ac, ll, rp in zip(models, acclist, lllist, rpslist):
        print(f" - {m:<18}: Acc={ac:.4f} | LogLoss={ll:.4f} | RPS={rp:.4f}")
        
    # Generate bar plots comparison
    # 1. Accuracy
    plt.figure(figsize=(7, 4.5), dpi=300)
    plt.bar(models, acclist, color=['#94A3B8', '#94A3B8', '#92C5FD', '#92C5FD', '#1D4ED8'], edgecolor='#1E3A8A', width=0.6)
    plt.title('Walk-Forward Cross-Validation Accuracy Comparison', fontsize=11, fontweight='bold', pad=15)
    plt.ylabel('Accuracy Score', fontsize=10)
    plt.ylim(min(acclist)-0.02, max(acclist)+0.015)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    for i, val in enumerate(acclist):
        plt.text(i, val + 0.002, f"{val:.2%}", ha='center', va='bottom', fontsize=8.5, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, "accuracy_comparison.png"))
    plt.close()
    
    # 2. Log Loss
    plt.figure(figsize=(7, 4.5), dpi=300)
    plt.bar(models, lllist, color=['#E2E8F0', '#FCA5A5', '#FCA5A5', '#FECACA', '#DC2626'], edgecolor='#7F1D1D', width=0.6)
    plt.title('Walk-Forward Cross-Validation Log Loss Comparison', fontsize=11, fontweight='bold', pad=15)
    plt.ylabel('Log Loss (Lower is Better)', fontsize=10)
    plt.ylim(min(lllist)-0.05, max(lllist)+0.05)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    for i, val in enumerate(lllist):
        plt.text(i, val + 0.005, f"{val:.4f}", ha='center', va='bottom', fontsize=8.5, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, "log_loss_comparison.png"))
    plt.close()

    # 3. RPS
    plt.figure(figsize=(7, 4.5), dpi=300)
    plt.bar(models, rpslist, color=['#E2E8F0', '#FDBA74', '#FDBA74', '#FFEDD5', '#EA580C'], edgecolor='#7C2D12', width=0.6)
    plt.title('Walk-Forward Cross-Validation RPS Comparison', fontsize=11, fontweight='bold', pad=15)
    plt.ylabel('Ranked Probability Score (Lower is Better)', fontsize=10)
    plt.ylim(min(rpslist)-0.01, max(rpslist)+0.01)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    for i, val in enumerate(rpslist):
        plt.text(i, val + 0.001, f"{val:.4f}", ha='center', va='bottom', fontsize=8.5, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, "rps_comparison.png"))
    plt.close()

    # 4. Confusion Matrix Heatmap
    cm = confusion_matrix(y_eval, np.argmax(pred_ens, axis=1))
    fig, ax = plt.subplots(figsize=(6, 5), dpi=300)
    cax = ax.matshow(cm, cmap='Blues')
    fig.colorbar(cax)
    
    classes = ['Draw', 'Home Win', 'Away Win']
    ax.set_xticklabels([''] + classes)
    ax.set_yticklabels([''] + classes)
    ax.tick_params(axis='both', which='major', labelsize=9)
    
    # Annotate values
    for (i, j), z in np.ndenumerate(cm):
        ax.text(j, i, '{:d}'.format(z), ha='center', va='center',
                color='white' if z > cm.max()/2. else 'black', fontweight='bold', fontsize=11)
                
    plt.title('Stacking Ensemble Confusion Matrix Heatmap', fontsize=11, fontweight='bold', pad=20)
    plt.xlabel('Predicted Class', fontsize=10, labelpad=10)
    ax.xaxis.set_label_position('top')
    plt.ylabel('True Class', fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, "confusion_matrix.png"))
    plt.close()

    # 5. Calibration Curve
    plt.figure(figsize=(8, 6), dpi=300)
    colors = ['#EA580C', '#2563EB', '#16A34A']
    labels = ['Draw', 'Home Win', 'Away Win']
    for i in range(3):
        prob_true, prob_pred = calibration_curve(
            (y_eval == i).astype(int), 
            pred_ens[:, i], 
            n_bins=8
        )
        plt.plot(prob_pred, prob_true, marker='o', label=f"{labels[i]}", color=colors[i], lw=1.5, ms=5)
        
    plt.plot([0, 1], [0, 1], linestyle='--', color='#64748B', label='Perfect Calibration', lw=1.2)
    plt.xlabel('Predicted Probability', fontsize=10)
    plt.ylabel('Empirical Frequency', fontsize=10)
    plt.title('Ensemble Calibration Curve (Reliability Diagram)', fontsize=11, fontweight='bold', pad=15)
    plt.legend(frameon=True, fontsize=9)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, "calibration_curve.png"))
    plt.close()

    # 6. Feature Importances: Train RF and XGB on full CV set to extract importances
    sw_full = compute_sample_weight('balanced', y)
    rf_model = RandomForestClassifier(n_estimators=500, max_features='sqrt', min_samples_leaf=5, class_weight='balanced', n_jobs=-1, random_state=42)
    rf_model.fit(X, y, sample_weight=sw_full)
    
    xgb_model = XGBClassifier(n_estimators=100, max_depth=4, random_state=42)
    xgb_model.fit(X, y, sample_weight=sw_full)
    
    features = [
        'Goals Scored Avg (H)', 'Goals Conceded Avg (H)', 'PPG Avg (H)',
        'Goals Scored Avg (A)', 'Goals Conceded Avg (A)', 'PPG Avg (A)',
        'Elo Difference'
    ]
    
    # RF Importances
    importances_rf = rf_model.feature_importances_
    indices_rf = np.argsort(importances_rf)
    
    plt.figure(figsize=(7, 4.5), dpi=300)
    plt.barh([features[i] for i in indices_rf], importances_rf[indices_rf], color='#3B82F6', edgecolor='#1D4ED8', height=0.5)
    plt.title('Feature Importance (Random Forest Base Model)', fontsize=11, fontweight='bold', pad=15)
    plt.xlabel('Mean Decrease in Impurity', fontsize=10)
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, "rf_feature_importance.png"))
    plt.close()
    
    # XGB Importances
    importances_xgb = xgb_model.feature_importances_
    indices_xgb = np.argsort(importances_xgb)
    
    plt.figure(figsize=(7, 4.5), dpi=300)
    plt.barh([features[i] for i in indices_xgb], importances_xgb[indices_xgb], color='#10B981', edgecolor='#047857', height=0.5)
    plt.title('Feature Importance (XGBoost Base Model)', fontsize=11, fontweight='bold', pad=15)
    plt.xlabel('F-Score / Weight', fontsize=10)
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, "xgb_feature_importance.png"))
    plt.close()

    # 7. ROC Curve One-vs-Rest for Stacking Ensemble
    plt.figure(figsize=(7, 5.5), dpi=300)
    for i in range(3):
        # Convert multiclass true label to binary one-vs-rest
        y_true_binary = (y_eval == i).astype(int)
        # Extract probas for class i
        y_score = pred_ens[:, i]
        fpr, tpr, _ = roc_curve(y_true_binary, y_score)
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, color=colors[i], lw=1.8, label=f"ROC {labels[i]} (AUC = {roc_auc:.3f})")
        
    plt.plot([0, 1], [0, 1], color='#64748B', linestyle='--', lw=1.2, label='Random Guess')
    plt.xlim([-0.01, 1.01])
    plt.ylim([-0.01, 1.01])
    plt.xlabel('False Positive Rate', fontsize=10)
    plt.ylabel('True Positive Rate', fontsize=10)
    plt.title('One-vs-Rest ROC Curve (Stacking Ensemble)', fontsize=11, fontweight='bold', pad=15)
    plt.legend(frameon=True, loc="lower right", fontsize=9)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, "roc_curve.png"))
    plt.close()
    
    print("[INFO] All validation and analytical charts generated successfully.")

if __name__ == "__main__":
    draw_overall_pipeline()
    evaluate_models()
