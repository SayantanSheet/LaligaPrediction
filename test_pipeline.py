import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')
from backend.poisson_model import validate_half_life
from backend.football_ensemble import FootballEnsembleEngine
from backend.football_predictor_xgb import main as test_xgb

print("--- TASK 2: DIXON-COLES SWEEP ---")
df = pd.read_json('src/data/matches-all-seasons.json')
df.rename(columns={'homeTeam':'home_team', 'awayTeam':'away_team', 'homeScore':'home_goals', 'awayScore':'away_goals'}, inplace=True)
validate_half_life(df)

print("\n--- TASK 3: META-LEARNER BENCHMARK ---")
df2 = pd.read_json('src/data/matches-all-seasons.json')
engine = FootballEnsembleEngine("")
engine.train(df2)

print("\n--- TASK 1: FULL CV RESULTS ---")
# evaluate main predictor pipeline
import os
test_xgb(json_path='src/data/matches-all-seasons.json', window=5, n_splits=5)

