import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
import datetime
from poisson_model import DixonColesPoissonModel
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import recall_score, log_loss, f1_score

# ===========================================================================
# STACKING ENSEMBLE ENGINE
# ===========================================================================

def walk_forward_split(X, n_splits=5, min_train_size=150):
    """
    FIX 1: Manual walk-forward splitter that enforces a minimum training set size.
    """
    n = len(X)
    if n <= min_train_size:
        return
        
    indices = np.arange(n)
    # Remaining samples after enforcing minimum training size
    rem = n - min_train_size
    test_size = rem // n_splits
    
    for i in range(n_splits):
        train_end = min_train_size + i * test_size
        test_end = train_end + test_size
        if i == n_splits - 1:
            test_end = n
            
        yield indices[:train_end], indices[train_end:test_end]


class FootballEnsembleEngine:
    """
    Production-ready stacking ensemble for match prediction.
    Aggregates: Poisson, XGBoost, LightGBM, Random Forest.
    """
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.poisson = DixonColesPoissonModel()
        self.rf = RandomForestClassifier(n_estimators=500, max_features='sqrt', min_samples_leaf=5, class_weight='balanced', n_jobs=-1, random_state=42)
        self.xgb = XGBClassifier(n_estimators=400, max_depth=4, learning_rate=0.05, n_jobs=-1, random_state=42)
        self.lgbm = LGBMClassifier(n_estimators=400, max_depth=4, learning_rate=0.05, n_jobs=-1, random_state=42, verbose=-1)
        
        # BUG 7 FIX - Upgrade meta-learner to XGBClassifier
        self.meta_learner = XGBClassifier(
            max_depth=2, 
            n_estimators=100, 
            learning_rate=0.05, 
            use_label_encoder=False, 
            eval_metric='mlogloss',
            random_state=42
        )
        
        self.df_history = None
        self.feature_cols_tree = []
        self.is_fitted = False

    def _prepare_data(self, df_raw: pd.DataFrame):
        """Prepare features for tree models and training."""
        df = df_raw.copy()
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
        
        # Simple Elo implementation if missing
        if 'home_elo' not in df.columns:
            df['home_elo'] = 1500.0
            df['away_elo'] = 1500.0
            
        # Outcome encoding
        if 'homeScore' in df.columns and 'awayScore' in df.columns:
            df['outcome'] = 0 # Draw
            df.loc[df['homeScore'] > df['awayScore'], 'outcome'] = 1 # Home Win
            df.loc[df['homeScore'] < df['awayScore'], 'outcome'] = 2 # Away Win
        
        return df

    def _compute_rolling_features(self, df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        Bug 1 Fix: Proper rolling features with shift(1) to avoid data leakage.
        """
        df = df.copy().sort_values('date') if 'date' in df.columns else df.copy()
        all_teams = pd.unique(df[['homeTeam', 'awayTeam']].values.ravel())
        
        # Initialize columns
        for col in ['home_roll_gs', 'home_roll_ga', 'home_ppg', 
                    'away_roll_gs', 'away_roll_ga', 'away_ppg']:
            df[col] = 0.0
            
        for team in all_teams:
            mask = (df['homeTeam'] == team) | (df['awayTeam'] == team)
            team_df = df[mask].copy()
            is_home = team_df['homeTeam'] == team
            gs = np.where(is_home, team_df['homeScore'], team_df['awayScore'])
            ga = np.where(is_home, team_df['awayScore'], team_df['homeScore'])
            
            def calculate_pts(h, a, team_is_home):
                if (team_is_home and h > a) or (not team_is_home and a > h): return 3
                if h == a: return 1
                return 0
            
            p = [calculate_pts(r['homeScore'], r['awayScore'], r['homeTeam'] == team) 
                 for _, r in team_df.iterrows()]
            
            s_gs = pd.Series(gs, index=team_df.index).shift(1)
            s_ga = pd.Series(ga, index=team_df.index).shift(1)
            s_p = pd.Series(p, index=team_df.index).shift(1)
            
            roll_gs = s_gs.rolling(window, min_periods=3).mean()
            roll_ga = s_ga.rolling(window, min_periods=3).mean()
            roll_ppg = s_p.rolling(window, min_periods=3).mean()
            
            df.loc[mask & (df['homeTeam'] == team), 'home_roll_gs'] = roll_gs
            df.loc[mask & (df['homeTeam'] == team), 'home_roll_ga'] = roll_ga
            df.loc[mask & (df['homeTeam'] == team), 'home_ppg'] = roll_ppg
            
            df.loc[mask & (df['awayTeam'] == team), 'away_roll_gs'] = roll_gs
            df.loc[mask & (df['awayTeam'] == team), 'away_roll_ga'] = roll_ga
            df.loc[mask & (df['awayTeam'] == team), 'away_ppg'] = roll_ppg
            
        return df.fillna(0.0)

    def _get_team_features(self, df: pd.DataFrame, team: str, date: Any):
        past = df[df['date'] < date].copy()
        team_matches = past[(past['homeTeam'] == team) | (past['awayTeam'] == team)].tail(10)
        if team_matches.empty:
            return {'ppg': 1.0, 'goals_avg': 1.0, 'gc_avg': 1.0, 'days_since': 14}
        points = []
        goals_for = []
        goals_ag = []
        for _, m in team_matches.iterrows():
            is_home = m['homeTeam'] == team
            gs = m['homeScore'] if is_home else m['awayScore']
            ga = m['awayScore'] if is_home else m['homeScore']
            goals_for.append(gs)
            goals_ag.append(ga)
            if gs > ga: points.append(3)
            elif gs == ga: points.append(1)
            else: points.append(0)
        last_match_date = team_matches['date'].max()
        days_since = (date - last_match_date).days
        return {
            'ppg': np.mean(points[-5:]) if points else 1.0,
            'goals_avg': np.mean(goals_for),
            'gc_avg': np.mean(goals_ag),
            'days_since': min(days_since, 30)
        }

    def train(self, df_raw: pd.DataFrame):
        df = self._prepare_data(df_raw)
        self.df_history = df
        df_feats = self._compute_rolling_features(df)
        poi_df = df.rename(columns={'homeTeam': 'home_team', 'awayTeam': 'away_team', 
                                    'homeScore': 'home_goals', 'awayScore': 'away_goals'})
        X_data = df_feats[[
            'home_roll_gs', 'home_roll_ga', 'home_ppg',
            'away_roll_gs', 'away_roll_ga', 'away_ppg'
        ]].copy()
        X_data['elo_difference'] = df['home_elo'].values - df['away_elo'].values
        y_data = df['outcome'].values
        start_idx = len(df) // 5
        X = X_data.iloc[start_idx:]
        y = y_data[start_idx:]
        self.feature_cols_tree = X.columns.tolist()
        
        tscv_iterator = list(walk_forward_split(X, n_splits=5, min_train_size=150))
        oof_matrix = np.zeros((len(X), 12)) 
        
        print(f"[INFO] Training base models and generating OOF predictions (folds={len(tscv_iterator)})...")
        for train_idx, val_idx in tscv_iterator:
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            sw = compute_sample_weight('balanced', y_train)
            rf_tmp = RandomForestClassifier(n_estimators=500, max_features='sqrt', min_samples_leaf=5, class_weight='balanced', n_jobs=-1, random_state=42)
            rf_tmp.fit(X_train, y_train, sample_weight=sw)
            xgb_tmp = XGBClassifier(n_estimators=100, max_depth=4, random_state=42).fit(X_train, y_train, sample_weight=sw)
            lgbm_tmp = LGBMClassifier(n_estimators=100, max_depth=4, random_state=42, verbose=-1).fit(X_train, y_train, sample_weight=sw)
            
            cutoff_date = df.iloc[start_idx + val_idx[0]]['date']
            poi_tmp = DixonColesPoissonModel().fit(poi_df, prediction_date=cutoff_date)
            
            p_rf = rf_tmp.predict_proba(X_val)
            p_xgb = xgb_tmp.predict_proba(X_val)
            p_lgbm = lgbm_tmp.predict_proba(X_val)
            
            p_poi = []
            for idx in val_idx:
                row = df.iloc[start_idx + idx]
                probs = poi_tmp.predict_proba(row['homeTeam'], row['awayTeam'])
                p_poi.append([probs['draw'], probs['home_win'], probs['away_win']])
            p_poi = np.array(p_poi)
            
            stacked = np.hstack([p_rf, p_xgb, p_lgbm, p_poi])
            oof_matrix[val_idx] = stacked
            
        used_idx = np.where(np.any(oof_matrix != 0, axis=1))[0]
        context_feats = df_feats.loc[X.index, ['home_ppg', 'away_ppg']].values
        elo_diff = (df.loc[X.index, 'home_elo'] - df.loc[X.index, 'away_elo']).values.reshape(-1, 1)
        X_meta_full = np.hstack([oof_matrix[used_idx], context_feats[used_idx], elo_diff[used_idx]])
        y_meta = y[used_idx]
        
        from sklearn.linear_model import LogisticRegression
        def rps_score(y_true, y_pred_proba):
            return np.mean([sum((np.cumsum(p) - np.cumsum(np.eye(3)[y]))**2)/2.0 
                            for y, p in zip(y_true, y_pred_proba)])
        
        tscv_meta_iterator = list(walk_forward_split(X_meta_full, n_splits=5, min_train_size=150))
        results_xgb = []
        results_lr = []
        for tx, vx in tscv_meta_iterator:
            X_tr, y_tr = X_meta_full[tx], y_meta[tx]
            X_te, y_te = X_meta_full[vx], y_meta[vx]
            w_tr = compute_sample_weight('balanced', y_tr)
            xgb_tmp = XGBClassifier(max_depth=2, n_estimators=100, learning_rate=0.05, random_state=42)
            xgb_tmp.fit(X_tr, y_tr, sample_weight=w_tr)
            p_xgb = xgb_tmp.predict_proba(X_te)
            lr_tmp = LogisticRegression(random_state=42, max_iter=1000)
            lr_tmp.fit(X_tr, y_tr, sample_weight=w_tr)
            p_lr = lr_tmp.predict_proba(X_te)
            results_xgb.append({
                'rps': rps_score(y_te, p_xgb),
                'll': log_loss(y_te, p_xgb),
                'f1': f1_score(y_te, np.argmax(p_xgb, axis=1), average='macro')
            })
            results_lr.append({
                'rps': rps_score(y_te, p_lr),
                'll': log_loss(y_te, p_lr),
                'f1': f1_score(y_te, np.argmax(p_lr, axis=1), average='macro'),
                'draw_recall': recall_score(y_te, np.argmax(p_lr, axis=1), labels=[0], average=None)[0]
            })
            
        mean_xgb_rps = np.mean([r['rps'] for r in results_xgb])
        mean_xgb_ll = np.mean([r['ll'] for r in results_xgb])
        mean_xgb_f1 = np.mean([r['f1'] for r in results_xgb])
        mean_lr_rps = np.mean([r['rps'] for r in results_lr])
        mean_lr_ll = np.mean([r['ll'] for r in results_lr])
        mean_lr_f1 = np.mean([r['f1'] for r in results_lr])
        mean_lr_draw_recall = np.mean([r['draw_recall'] for r in results_lr])
        
        print(f"\n{'='*55}")
        print(f"  META-LEARNER BENCHMARK")
        print(f"{'='*55}")
        print(f"{'MetaLearner':<15} | {'mean_rps':<10} | {'mean_log_loss':<15} | {'mean_macro_f1':<15} | {'draw_recall':<12}")
        print(f"{'XGBoost':<15} | {mean_xgb_rps:<10.4f} | {mean_xgb_ll:<15.4f} | {mean_xgb_f1:<15.4f} | {'N/A':<12}")
        print(f"{'LogReg':<15} | {mean_lr_rps:<10.4f} | {mean_lr_ll:<15.4f} | {mean_lr_f1:<15.4f} | {mean_lr_draw_recall:<12.4f}")
        
        rps_diff = mean_lr_rps - mean_xgb_rps
        if rps_diff > 0.005:
            self.meta_learner = XGBClassifier(max_depth=2, n_estimators=100, learning_rate=0.05, eval_metric='mlogloss', random_state=42)
        else:
            self.meta_learner = LogisticRegression(random_state=42, max_iter=1000)
            
        sw_meta = compute_sample_weight('balanced', y_meta)
        self.meta_learner.fit(X_meta_full, y_meta, sample_weight=sw_meta)
        
        sw_final = compute_sample_weight('balanced', y)
        self.rf.fit(X, y, sample_weight=sw_final)
        self.xgb.fit(X, y, sample_weight=sw_final)
        self.lgbm.fit(X, y, sample_weight=sw_final)
        self.poisson.fit(poi_df)
        self.is_fitted = True
        print("[INFO] Ensemble training complete.")

    def predict(self, home_team: str, away_team: str, 
                home_injured: bool = False, away_injured: bool = False) -> Dict:
        if not self.is_fitted: return {"error": "Model not fitted"}
        p_poi_dict = self.poisson.predict_proba(home_team, away_team)
        p_poi = np.array([[p_poi_dict['draw'], p_poi_dict['home_win'], p_poi_dict['away_win']]])
        latest_date = self.df_history['date'].max() + pd.Timedelta(days=7)
        h_feat = self._get_team_features(self.df_history, home_team, latest_date)
        a_feat = self._get_team_features(self.df_history, away_team, latest_date)
        h_elo = self.df_history[self.df_history['homeTeam'] == home_team]['home_elo'].iloc[-1] if not self.df_history[self.df_history['homeTeam'] == home_team].empty else 1500.0
        a_elo = self.df_history[self.df_history['awayTeam'] == away_team]['away_elo'].iloc[-1] if not self.df_history[self.df_history['awayTeam'] == away_team].empty else 1500.0
        X_tree = pd.DataFrame([{'home_roll_gs': h_feat['goals_avg'], 'home_roll_ga': h_feat['gc_avg'], 'home_ppg': h_feat['ppg'],
                                'away_roll_gs': a_feat['goals_avg'], 'away_roll_ga': a_feat['gc_avg'], 'away_ppg': a_feat['ppg'],
                                'elo_difference': h_elo - a_elo}])[self.feature_cols_tree]
        p_rf = self.rf.predict_proba(X_tree)
        p_xgb = self.xgb.predict_proba(X_tree)
        p_lgbm = self.lgbm.predict_proba(X_tree)
        context = np.array([[h_feat['ppg'], a_feat['ppg'], h_elo - a_elo]])
        X_meta = np.hstack([p_rf, p_xgb, p_lgbm, p_poi, context])
        proba = self.meta_learner.predict_proba(X_meta)[0]
        label_idx = np.argmax(proba)
        conf = "high" if proba[label_idx] > 0.6 else "medium" if proba[label_idx] > 0.4 else "low"
        return {
            "home_win": round(proba[1], 4), "draw": round(proba[0], 4), "away_win": round(proba[2], 4),
            "confidence": conf, "most_likely_score": p_poi_dict['most_likely_score'],
            "base_models": {
                "poisson": p_poi_dict,
                "rf": p_rf[0].tolist(),
                "xgb": p_xgb[0].tolist(),
                "lgbm": p_lgbm[0].tolist()
            }
        }
