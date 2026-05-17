import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, f1_score, log_loss
from backend.poisson_model import DixonColesPoissonModel, validate_half_life
from backend.football_ensemble import FootballEnsembleEngine
from backend.football_predictor_xgb import load_csv_matches, generate_synthetic_data, ranked_probability_score
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression
import warnings
warnings.filterwarnings('ignore')

def evaluate_predictions(y_true, y_proba):
    y_pred = np.argmax(y_proba, axis=1)
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    rps = np.mean([ranked_probability_score(y, p) for y, p in zip(y_true, y_proba)])
    ll = log_loss(y_true, y_proba, labels=[0, 1, 2])
    return {"acc": acc, "f1": f1, "rps": rps, "log_loss": ll}

def task1_and_3():
    # Load dataset
    df = pd.DataFrame()
    try:
        with open('src/data/matches-all-seasons.json') as f:
            import json
            raw = json.load(f)
            df_list = []
            for m in raw:
                m['homeTeam'] = " ".join(m['homeTeam'].replace('\n', ' ').split()).strip()
                m['awayTeam'] = " ".join(m['awayTeam'].replace('\n', ' ').split()).strip()
                df_list.append(m)
            df = pd.DataFrame(df_list)
    except:
        df = generate_synthetic_data(n_teams=12, seasons=4)
        df.rename(columns={'home_team': 'homeTeam', 'away_team': 'awayTeam', 'home_goals': 'homeScore', 'away_goals': 'awayScore'}, inplace=True)
    
    # We want to do a Holdout Evaluation on the last 15% and a CV on the first 85%.
    n = len(df)
    cut = int(n * 0.85)
    df_cv = df.iloc[:cut].copy()
    df_ho = df.iloc[cut:].copy()
    
    engine = FootballEnsembleEngine("")
    
    # Let's write the CV specifically for the ensemble
    # Actually, we can just run engine.train() which creates OOF from TSCV.
    # We can evaluate the OOF predictions!
    # Wait, if we evaluate the meta-learner, we need to do OOF on the meta-learner too, 
    # OR since the meta-learner is very simple (XGB depth=2 / LogReg), we can just do 
    # a TimeSeriesSplit on the OOF matrix to evaluate the meta-learner!
    
    pass

