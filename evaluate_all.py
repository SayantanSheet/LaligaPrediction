import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from backend.poisson_model import DixonColesPoissonModel, validate_half_life
from backend.football_ensemble import FootballEnsembleEngine
from sklearn.metrics import accuracy_score, f1_score, log_loss
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression
import warnings

warnings.filterwarnings('ignore')

BASELINE_RPS = 0.2091
BASELINE_LL = 2.334
BASELINE_ACC = 0.4875

def task2_poisson_sweep(df):
    print("\n--- TASK 2: DIXON-COLES HALF-LIFE SWEEP ---")
    best_hl = validate_half_life(df)
    
    # Regression assert
    assert best_hl in [30, 60, 90, 120, 180, 365], "Best half-life must be one of the candidate values"
    
def task3_benchmark_metalearner(df):
    print("\n--- TASK 3: META-LEARNER BENCHMARK ---")
    # We will simulate the meta-learner benchmark on OOF predictions.
    pass

def main():
    df = pd.read_json('src/data/matches-all-seasons.json')
    df.rename(columns={'homeTeam':'home_team', 'awayTeam':'away_team', 'homeScore':'home_goals', 'awayScore':'away_goals'}, inplace=True)
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    task2_poisson_sweep(df)

if __name__ == "__main__":
    main()
