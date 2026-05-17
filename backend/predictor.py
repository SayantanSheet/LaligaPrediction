import json
import os
import math
import pandas as pd
from football_ensemble import FootballEnsembleEngine
from player_data import get_player_stats

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(PROJECT_ROOT, 'src/data/matches-all-seasons.json')

class PredictionEngine:
    def __init__(self):
        self.matches = []
        self.ensemble = FootballEnsembleEngine(DATA_FILE)
        self.is_ready = False
        self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
                df_list = []
                for m in raw:
                    m['homeTeam'] = " ".join(m['homeTeam'].replace('\n', ' ').split()).strip()
                    m['awayTeam'] = " ".join(m['awayTeam'].replace('\n', ' ').split()).strip()
                    df_list.append(m)
                self.matches = df_list
            
            # Train Ensemble Engine
            print("[PredictionEngine] Training Stacking Ensemble...")
            df = pd.DataFrame(self.matches)
            try:
                self.ensemble.train(df)
                self.is_ready = True
                print("[PredictionEngine] Ensemble ready.")
            except Exception as e:
                print(f"[ERROR] Failed to train ensemble: {e}")
                self.is_ready = False
        else:
            self.matches = []
            self.is_ready = False

    def get_teams(self):
        teams = set()
        for m in self.matches:
            teams.add(m['homeTeam'])
            teams.add(m['awayTeam'])
        return sorted(list(teams))

    def get_h2h_history(self, team1, team2):
        """Returns the last 5 matches between two teams."""
        h2h = []
        for m in self.matches:
            if (m['homeTeam'] == team1 and m['awayTeam'] == team2) or \
               (m['homeTeam'] == team2 and m['awayTeam'] == team1):
                h2h.append(m)
        
        # Sort by date descending and take top 5
        h2h.sort(key=lambda x: x['date'], reverse=True)
        return h2h[:5]

    def predict_match(self, home_team, away_team):
        if not self.is_ready:
            return {"error": "Engine not ready. Ensure match data exists and model is trained."}

        # Fetch Player Data & Injury Status
        home_player_stats = get_player_stats(home_team)
        away_player_stats = get_player_stats(away_team)
        
        home_injured = home_player_stats["key_injured"]
        away_injured = away_player_stats["key_injured"]

        # Predict using Ensemble Engine
        result = self.ensemble.predict(home_team, away_team, home_injured, away_injured)
        
        if "error" in result:
            return {"error": f"Ensemble error: {result['error']}"}

        # Format the response for the frontend
        home_win_prob = result['home_win'] * 100
        draw_prob = result['draw'] * 100
        away_win_prob = result['away_win'] * 100
        
        predicted_score = result['most_likely_score']
        confidence_val = max(result['home_win'], result['draw'], result['away_win'])

        # Calculate basic form and stats for the frontend
        def get_team_stats(team):
            team_matches = [m for m in self.matches if m['homeTeam'] == team or m['awayTeam'] == team]
            played = len(team_matches)
            if played == 0:
                return {"avg_scored": 0, "avg_conceded": 0, "played": 0, "strength": "AVERAGE"}
            
            gs = sum([m['homeScore'] if m['homeTeam'] == team else m['awayScore'] for m in team_matches])
            gc = sum([m['awayScore'] if m['homeTeam'] == team else m['homeScore'] for m in team_matches])
            avg_s = gs / played
            return {
                "avg_scored": round(avg_s, 2),
                "avg_conceded": round(gc / played, 2),
                "played": played,
                "strength": "STRONG" if avg_s > 1.5 else "AVERAGE" if avg_s > 1.0 else "WEAK"
            }

        def get_recent_form(team):
            team_matches = [m for m in self.matches if m['homeTeam'] == team or m['awayTeam'] == team]
            team_matches.sort(key=lambda x: x['date'], reverse=True)
            recent = team_matches[:5]
            history = []
            pts = 0
            for m in recent:
                is_home = m['homeTeam'] == team
                score = m['homeScore'] if is_home else m['awayScore']
                opp = m['awayScore'] if is_home else m['homeScore']
                if score > opp: 
                    outcome, p = "Win", 3
                elif score == opp: 
                    outcome, p = "Draw", 1
                else: 
                    outcome, p = "Loss", 0
                
                history.append({
                    "date": m['date'], 
                    "opponent": m['awayTeam'] if is_home else m['homeTeam'], 
                    "outcome": outcome, 
                    "score": f"{score}-{opp}"
                })
                pts += p
            
            return {
                "match_history": history, 
                "points": pts, 
                "label": "GOOD FORM" if pts >= 10 else "STABLE" if pts >= 6 else "POOR FORM"
            }

        h_stats = get_team_stats(home_team)
        a_stats = get_team_stats(away_team)
        
        # Add Poisson Lambda (expected goals) for the frontend HomeAwayPerformance fix
        h_stats['lambda'] = result['base_models']['poisson']['expected_goals_home']
        a_stats['lambda'] = result['base_models']['poisson']['expected_goals_away']
        
        h_form = get_recent_form(home_team)
        a_form = get_recent_form(away_team)

        # Market analysis using ensemble probabilities
        over_1_5 = round(min(98, (1 - result['base_models']['poisson'].get('matrix_0_0', 0.05)) * 100), 1)
        # Simplified market proxies
        over_2_5 = round((1 - result['draw'] * 0.8) * 75, 1)
        btts = round((1 - result['draw'] * 0.5) * 65, 1)

        # Calculate variance between Poisson and Meta-learner for the UI
        poi_prob = result['base_models']['poisson']['home_win']
        meta_prob = result['home_win']
        variance_val = round(abs(poi_prob - meta_prob) * 100, 1)

        return {
            "home_team": home_team,
            "away_team": away_team,
            "predicted_score": predicted_score,
            "probabilities": {
                "home_win": home_win_prob / 100,
                "draw": draw_prob / 100,
                "away_win": away_win_prob / 100
            },
            "poisson_probs": {
                "home": round(result['base_models']['poisson']['home_win'] * 100, 1),
                "draw": round(result['base_models']['poisson']['draw'] * 100, 1),
                "away": round(result['base_models']['poisson']['away_win'] * 100, 1)
            },
            "rf_probs": {
                "home": round(result['base_models']['rf'][1] * 100, 1),
                "draw": round(result['base_models']['rf'][0] * 100, 1),
                "away": round(result['base_models']['rf'][2] * 100, 1)
            },
            "confidence": round(confidence_val * 100, 1),
            "comparison": {
                "agreement": "HIGH" if result['confidence'] == "high" else "MEDIUM" if result['confidence'] == "medium" else "LOW",
                "variance": variance_val,
                "recommendation": "Ensemble Optimized Prediction"
            },
            "market_analysis": {
                "over_1_5": over_1_5,
                "over_2_5": over_2_5,
                "btts": btts
            },
            "performance_analysis": {
                "home": h_stats,
                "away": a_stats
            },
            "form_analysis": {
                "home": h_form,
                "away": a_form,
                "momentum_gap": h_form['points'] - a_form['points']
            },
            "insights": {
                "poisson": f"Dixon-Coles Analysis projects {predicted_score} based on attacking parameters.",
                "predictor": f"Stacking ensemble combines 4 models for high-variance capture."
            },
            "player_impact": {
                "home_key_player": home_player_stats,
                "away_key_player": away_player_stats,
                "home_injured": home_injured,
                "away_injured": away_injured,
                "insight": f"Injury to {home_player_stats['top_scorer']} reduces {home_team} win probability." if home_injured else "Full squad available for key players."
            },
            "h2h_history": self.get_h2h_history(home_team, away_team)
        }

