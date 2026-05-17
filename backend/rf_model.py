import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from category_encoders import OrdinalEncoder
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, f1_score
from typing import List, Dict, Any, Tuple

class RandomForestModel:
    """ Improved RF Model with Temporal Safety and Categorical Encoding """
    
    def __init__(self, n_estimators=500):
        self.clf = RandomForestClassifier(
            n_estimators=n_estimators,
            max_features='sqrt',
            min_samples_leaf=5,
            class_weight='balanced',
            n_jobs=-1,
            random_state=42
        )
        self.team_enc = None
        self.is_fitted = False
        self.feature_cols = []

    def _prepare_features(self, df: pd.DataFrame, is_training: bool = True) -> Tuple[pd.DataFrame, pd.Series]:
        df = df.copy().sort_values('date')
        
        # FIX 2 - Use OrdinalEncoder with handle_unknown='value'
        if is_training:
            self.team_enc = OrdinalEncoder(
                cols=['home_team', 'away_team'], 
                handle_unknown='value', 
                handle_missing='value'
            )
            df[['home_id', 'away_id']] = self.team_enc.fit_transform(df[['home_team', 'away_team']])
        else:
            df[['home_id', 'away_id']] = self.team_enc.transform(df[['home_team', 'away_team']])
        
        # FIX 2 - Impute unknown teams (-1) with 0 (neutral prior)
        df['home_id'] = df['home_id'].replace(-1, 0)
        df['away_id'] = df['away_id'].replace(-1, 0)
        
        # Simple rolling features
        for team in pd.unique(df[['home_team', 'away_team']].values.ravel()):
            mask = (df['home_team'] == team) | (df['away_team'] == team)
            team_df = df[mask].copy()
            # Canonical shift(1) to prevent leakage
            scored = np.where(team_df['home_team'] == team, team_df['home_goals'], team_df['away_goals'])
            team_df['roll_gf'] = pd.Series(scored, index=team_df.index).shift(1).rolling(5, min_periods=1).mean()
            df.loc[mask & (df['home_team'] == team), 'home_roll_gf'] = team_df['roll_gf']
            df.loc[mask & (df['away_team'] == team), 'away_roll_gf'] = team_df['roll_gf']

        features = ['home_id', 'away_id', 'home_roll_gf', 'away_roll_gf']
        df = df.fillna(0)
        
        # Outcome encoding
        df['outcome'] = 0
        df.loc[df['home_goals'] > df['away_goals'], 'outcome'] = 1
        df.loc[df['home_goals'] < df['away_goals'], 'outcome'] = 2
        
        self.feature_cols = features
        return df[features], df['outcome']

    def cross_validate(self, df: pd.DataFrame, n_splits: int = 5):
        """ FIX 1 - Replacing Random CV with TimeSeriesSplit """
        tscv = TimeSeriesSplit(n_splits=n_splits)
        X, y = self._prepare_features(df, is_training=True)
        
        metrics = []
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X), start=1):
            # FIX 1 — Regression Assert for Temporal Split
            assert max(train_idx) < min(val_idx), f"Fold {fold} leakage: train and val indices overlap temporally"
            
            X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            self.clf.fit(X_tr, y_tr)
            y_pred = self.clf.predict(X_val)
            
            acc = accuracy_score(y_val, y_pred)
            f1 = f1_score(y_val, y_pred, average='macro')
            metrics.append({'fold': fold, 'acc': acc, 'f1': f1})
            print(f"Fold {fold} | Acc: {acc:.4f} | F1: {f1:.4f}")
            
        print(f"Mean Acc: {np.mean([m['acc'] for m in metrics]):.4f}")
        return metrics

    def fit(self, df: pd.DataFrame):
        X, y = self._prepare_features(df, is_training=True)
        self.clf.fit(X, y)
        self.is_fitted = True
        return self

    def predict_proba(self, df: pd.DataFrame):
        X, _ = self._prepare_features(df, is_training=False)
        return self.clf.predict_proba(X)

if __name__ == "__main__":
    # Test unknown team handling
    from football_predictor_xgb import generate_synthetic_data
    df = generate_synthetic_data()
    model = RandomForestModel()
    model.fit(df)
    
    test_df = pd.DataFrame([{
        'date': pd.Timestamp.now(), 'home_team': 'NEW_TEAM_X', 'away_team': 'Team_A',
        'home_goals': 0, 'away_goals': 0
    }])
    X_test, _ = model._prepare_features(test_df, is_training=False)
    # FIX 2 - Regression Assert for Unknown Teams
    assert X_test.iloc[0]['home_id'] == 0, f"Unseen team should map to 0, got {X_test.iloc[0]['home_id']}"
    print("Regression test for Fix 2: PASSED")
