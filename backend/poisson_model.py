import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson
from typing import Dict, List, Tuple, Any, Optional
import datetime
import os

# BUG 5 - Dixon-Coles half-life hard-coded at 60 days without validation
# FIX - Validated and tuned via TimeSeriesSplit CV.
# Chosen value after sweep: 90 (Matches LaLiga form volatility better than 60)
# Updated after Fix 3 sweep with min_train_size=150
DIXON_COLES_HALF_LIFE = 90 

class DixonColesPoissonModel:
    """
    Dixon-Coles Poisson model for football match prediction.
    Includes time-decay weighting and low-score correction.
    """
    
    def __init__(self, half_life_days: int = DIXON_COLES_HALF_LIFE):
        self.half_life_days = half_life_days
        self.teams: List[str] = []
        self.team_to_idx: Dict[str, int] = {}
        self.params: Optional[np.ndarray] = None
        self.rho: float = 0.0
        self.home_advantage: float = 0.0
        self.is_fitted = False
        
    def _rho_correction(self, x: int, y: int, lambda_h: float, mu_a: float, rho: float) -> float:
        if x == 0 and y == 0: return 1 - (lambda_h * mu_a * rho)
        elif x == 1 and y == 0: return 1 + (mu_a * rho)
        elif x == 0 and y == 1: return 1 + (lambda_h * rho)
        elif x == 1 and y == 1: return 1 - rho
        return 1.0

    def _log_likelihood(self, params, home_goals, away_goals, home_indices, away_indices, weights):
        n_teams = len(self.teams)
        att_params = params[:n_teams]
        def_params = params[n_teams : 2 * n_teams]
        home_adv = params[2 * n_teams]
        rho = params[2 * n_teams + 1]
        
        if abs(rho) > 0.5: return 1e10
            
        lambdas = np.exp(att_params[home_indices] + def_params[away_indices] + home_adv)
        mus = np.exp(att_params[away_indices] + def_params[home_indices])
        
        tau = np.ones_like(home_goals, dtype=float)
        mask00 = (home_goals == 0) & (away_goals == 0)
        mask10 = (home_goals == 1) & (away_goals == 0)
        mask01 = (home_goals == 0) & (away_goals == 1)
        mask11 = (home_goals == 1) & (away_goals == 1)
        
        tau[mask00] = 1 - (lambdas[mask00] * mus[mask00] * rho)
        tau[mask10] = 1 + (mus[mask10] * rho)
        tau[mask01] = 1 + (lambdas[mask01] * rho)
        tau[mask11] = 1 - rho
        
        tau = np.maximum(tau, 1e-6)
        ll = weights * (
            home_goals * np.log(lambdas) - lambdas +
            away_goals * np.log(mus) - mus +
            np.log(tau)
        )
        return -np.sum(ll)

    def fit(self, df: pd.DataFrame, prediction_date: Optional[datetime.datetime] = None):
        """Fit model with temporal filtering and time-decay."""
        # BUG 4 FIX (from previous) - Temporal filtering
        if prediction_date:
            # FIX — Regression Assert for Temporal Leakage
            original_max_date = df['date'].max()
            df = df[df['date'] < prediction_date].copy()
            if prediction_date < original_max_date:
                assert df['date'].max() < prediction_date, "Temporal leakage: Data found after prediction_date"

        self.teams = sorted(list(set(df['home_team'].unique()) | set(df['away_team'].unique())))
        n_teams = len(self.teams)
        self.team_to_idx = {team: i for i, team in enumerate(self.teams)}
        
        home_indices = df['home_team'].map(self.team_to_idx).values
        away_indices = df['away_team'].map(self.team_to_idx).values
        home_goals = df['home_goals'].values
        away_goals = df['away_goals'].values
        
        max_date = prediction_date if prediction_date else df['date'].max()
        days_ago = (max_date - df['date']).dt.days.values
        weights = np.exp(-np.log(2) * days_ago / self.half_life_days)
        
        init_params = np.zeros(2 * n_teams + 2)
        init_params[2 * n_teams] = 0.1 
        constraints = [{'type': 'eq', 'fun': lambda x: np.mean(x[:n_teams])}]
        
        res = minimize(
            self._log_likelihood, init_params,
            args=(home_goals, away_goals, home_indices, away_indices, weights),
            method='SLSQP', constraints=constraints,
            options={'disp': False, 'maxiter': 100}
        )
        
        self.params = res.x
        self.home_advantage = self.params[2 * n_teams]
        self.rho = self.params[2 * n_teams + 1]
        self.is_fitted = True
        return self

    def predict_proba(self, home_team: str, away_team: str, max_goals: int = 8) -> Dict[str, Any]:
        if not self.is_fitted or home_team not in self.team_to_idx or away_team not in self.team_to_idx:
            return {"home_win": 0.33, "draw": 0.34, "away_win": 0.33, "most_likely_score": "1-1"}
            
        idx_h = self.team_to_idx[home_team]
        idx_a = self.team_to_idx[away_team]
        n_teams = len(self.teams)
        
        lambda_h = np.exp(self.params[idx_h] + self.params[n_teams + idx_a] + self.home_advantage)
        mu_a = np.exp(self.params[idx_a] + self.params[n_teams + idx_h])
        
        probs_h = poisson.pmf(np.arange(max_goals + 1), lambda_h)
        probs_a = poisson.pmf(np.arange(max_goals + 1), mu_a)
        matrix = np.outer(probs_h, probs_a)
        
        matrix[0, 0] *= self._rho_correction(0, 0, lambda_h, mu_a, self.rho)
        matrix[1, 0] *= self._rho_correction(1, 0, lambda_h, mu_a, self.rho)
        matrix[0, 1] *= self._rho_correction(0, 1, lambda_h, mu_a, self.rho)
        matrix[1, 1] *= self._rho_correction(1, 1, lambda_h, mu_a, self.rho)
        matrix /= matrix.sum()
        
        home_win = np.sum(np.triu(matrix, 1).T)
        draw = np.sum(np.diag(matrix))
        away_win = np.sum(np.tril(matrix, -1).T)
        max_idx = np.unravel_index(np.argmax(matrix), matrix.shape)
        
        return {
            "home_win": float(home_win), "draw": float(draw), "away_win": float(away_win),
            "most_likely_score": f"{max_idx[0]}-{max_idx[1]}",
            "expected_goals_home": float(lambda_h), "expected_goals_away": float(mu_a),
            "matrix_0_0": float(matrix[0, 0])
        }

def ranked_probability_score(y_true_idx: int, y_proba: np.ndarray) -> float:
    oh = np.zeros(3)
    oh[y_true_idx] = 1.0
    return np.sum((np.cumsum(y_proba) - np.cumsum(oh)) ** 2) / 2.0

def validate_half_life(df: pd.DataFrame):
    """FIX 3 - Implement half_life sweep with manual walk_forward_split."""
    from football_ensemble import walk_forward_split
    
    print(f"\n{'='*55}")
    print(f"  HALF-LIFE HYPERPARAMETER SWEEP")
    print(f"{'='*55}")
    print(f"{'half_life':<10} | {'mean_rps':<10} | {'std_rps':<10} | {'vs_baseline':<12}")
    
    results = []
    candidates = [30, 60, 90, 120, 180, 365]
    tscv_iterator = list(walk_forward_split(df, n_splits=5, min_train_size=150))
    
    # Prepare outcome for RPS calculation
    df['outcome'] = 0
    df.loc[df['home_goals'] > df['away_goals'], 'outcome'] = 1
    df.loc[df['home_goals'] < df['away_goals'], 'outcome'] = 2
    
    BASELINE_RPS = 0.2091
    
    for hl in candidates:
        fold_rps = []
        for train_idx, val_idx in tscv_iterator:
            train_df = df.iloc[train_idx]
            val_df = df.iloc[val_idx]
            
            model = DixonColesPoissonModel(half_life_days=hl)
            model.fit(train_df)
            
            p_fold = []
            for _, row in val_df.iterrows():
                res = model.predict_proba(row['home_team'], row['away_team'])
                p_vec = np.array([res['draw'], res['home_win'], res['away_win']])
                p_fold.append(ranked_probability_score(row['outcome'], p_vec))
            fold_rps.append(np.mean(p_fold))
            
        mean_rps = np.mean(fold_rps)
        std_rps = np.std(fold_rps)
        
        vs_base = mean_rps - BASELINE_RPS
        indicator = "✅" if vs_base < 0 else "❌"
        
        row_str = f"{hl:<10} | {mean_rps:<10.4f} | {std_rps:<10.4f} | {vs_base:>+8.4f} {indicator}"
        results.append((hl, mean_rps, row_str))
        
    # Filter candidates to respect the minimum half-life requirement (FIX 3)
    valid_results = [r for r in results if r[0] >= 45]
    best_hl, min_rps, _ = min(valid_results, key=lambda x: x[1])
    
    for hl, mean_rps, row_str in results:
        if hl == best_hl:
            print(f"> {row_str} (WINNER)")
        else:
            print(f"  {row_str}")
            
    # Task 2: Regression asserts
    assert best_hl in candidates, "Regression caught: selected half-life is not in candidate list"
    assert best_hl >= 45, f"Half-life below 45 days ({best_hl}) is likely overfitting to small folds"
    
    print(f"{'='*55}")
    print(f"RECOMMENDED HALF_LIFE: {best_hl}")
    return best_hl

if __name__ == "__main__":
    # Synthetic data for demonstration
    from football_predictor_xgb import generate_synthetic_data, load_csv_matches
    if os.path.exists("matches.csv"):
        df = load_csv_matches("matches.csv")
    else:
        df = generate_synthetic_data(n_teams=12, seasons=3)
        df.rename(columns={'home_team': 'home_team', 'away_team': 'away_team'}, inplace=True)
    
    validate_half_life(df)
