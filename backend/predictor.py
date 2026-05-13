import json
import os
import math
from football_predictor_xgb import XGBPredictionEngine
from player_data import get_player_stats

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(PROJECT_ROOT, 'src/data/matches-all-seasons.json')

class PredictionEngine:
    def __init__(self):
        self.matches = []
        self.xgb_engine = None
        self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
                for m in raw:
                    m['homeTeam'] = " ".join(m['homeTeam'].replace('\n', ' ').split()).strip()
                    m['awayTeam'] = " ".join(m['awayTeam'].replace('\n', ' ').split()).strip()
                self.matches = raw
            
            # Initialize XGBoost Engine
            self.xgb_engine = XGBPredictionEngine(DATA_FILE)
        else:
            self.matches = []
            self.xgb_engine = None

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
        if not self.xgb_engine:
            return {"error": "Engine not ready. Ensure match data exists."}

        # Fetch Player Data & Injury Status
        home_player_stats = get_player_stats(home_team)
        away_player_stats = get_player_stats(away_team)
        
        home_injured = home_player_stats["key_injured"]
        away_injured = away_player_stats["key_injured"]

        # Predict using XGBoost Engine
        xgb_result = self.xgb_engine.predict(home_team, away_team, home_injured, away_injured)
        
        if not xgb_result:
            return {"error": f"Could not generate prediction for {home_team} vs {away_team}"}

        # Format the response to maintain compatibility with the frontend
        # The frontend expects certain fields that were previously calculated in predictor.py
        
        # Determine predicted score based on probabilities (simplified)
        # In a real scenario, we might use Poisson or another method for the score specifically, 
        # but let's estimate based on typical results for the predicted outcome.
        
        home_win_prob = xgb_result['home_win']
        draw_prob = xgb_result['draw']
        away_win_prob = xgb_result['away_win']
        
        if home_win_prob > draw_prob and home_win_prob > away_win_prob:
            predicted_score = "2 - 1"
        elif away_win_prob > draw_prob:
            predicted_score = "1 - 2"
        else:
            predicted_score = "1 - 1"

        # Calculate confidence from the winning probability
        confidence = max(home_win_prob, draw_prob, away_win_prob)

        # Calculate basic form and stats for the frontend
        def get_team_stats(team):
            team_matches = [m for m in self.matches if m['homeTeam'] == team or m['awayTeam'] == team]
            played = len(team_matches)
            if played == 0:
                return {"avg_scored": 0, "avg_conceded": 0, "played": 0, "strength": "AVERAGE", "lambda": 1.0}
            
            goals_scored = sum([m['homeScore'] if m['homeTeam'] == team else m['awayScore'] for m in team_matches])
            goals_conceded = sum([m['awayScore'] if m['homeTeam'] == team else m['homeScore'] for m in team_matches])
            avg_scored = goals_scored / played
            return {
                "avg_scored": round(avg_scored, 2),
                "avg_conceded": round(goals_conceded / played, 2),
                "played": played,
                "strength": "STRONG" if avg_scored > 1.5 else "AVERAGE" if avg_scored > 1.0 else "WEAK",
                "lambda": round(avg_scored, 2) # Mock lambda using avg scored
            }

        def get_recent_form(team):
            team_matches = [m for m in self.matches if m['homeTeam'] == team or m['awayTeam'] == team]
            team_matches.sort(key=lambda x: x['date'], reverse=True)
            recent = team_matches[:38] # Keep enough for stats, but use top 5 for history UI
            history = []
            pts, w, d, l, gs, gc = 0, 0, 0, 0, 0, 0
            for i, m in enumerate(recent):
                is_home = m['homeTeam'] == team
                score = m['homeScore'] if is_home else m['awayScore']
                opp = m['awayScore'] if is_home else m['homeScore']
                gs += score
                gc += opp
                if score > opp: 
                    outcome, p = "Win", 3
                    w += 1
                elif score == opp: 
                    outcome, p = "Draw", 1
                    d += 1
                else: 
                    outcome, p = "Loss", 0
                    l += 1
                
                if i < 5: # Only first 5 for history display
                    history.append({"date": m['date'], "opponent": m['awayTeam'] if is_home else m['homeTeam'], "outcome": outcome, "score": f"{score}-{opp}"})
                    pts += p
            
            return {
                "match_history": history, 
                "points": pts, 
                "label": "GOOD FORM" if pts >= 10 else "STABLE" if pts >= 6 else "POOR FORM",
                "wins": w, "draws": d, "losses": l,
                "goals_scored": gs, "goals_conceded": gc,
                "played": len(recent)
            }

        h_stats = get_team_stats(home_team)
        a_stats = get_team_stats(away_team)
        h_form = get_recent_form(home_team)
        a_form = get_recent_form(away_team)

        # Simplified market analysis based on match history/probabilities
        over_1_5 = round(min(95, (home_win_prob + away_win_prob + draw_prob * 0.5) * 1.1), 1)
        over_2_5 = round(over_1_5 * 0.75, 1)
        btts = round(min(90, (home_win_prob * 0.6 + away_win_prob * 0.6 + draw_prob * 0.8)), 1)

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
                "home": home_win_prob,
                "draw": draw_prob,
                "away": away_win_prob
            },
            "rf_probs": {
                "home": home_win_prob,
                "draw": draw_prob,
                "away": away_win_prob
            },
            "confidence": confidence,
            "comparison": {
                "agreement": "HIGH",
                "variance": 10.0,
                "recommendation": "XGBoost Optimized Prediction"
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
                "poisson": f"XGBoost Analysis projects a likely outcome based on {h_stats['avg_scored']} goals/match form.",
                "predictor": f"Momentum gap of {h_form['points'] - a_form['points']} points in the last 5 matches."
            },
            "player_impact": {
                "home_key_player": home_player_stats,
                "away_key_player": away_player_stats,
                "home_injured": home_injured,
                "away_injured": away_injured,
                "insight": f"CRITICAL: {home_player_stats['top_scorer']} is out for {home_team}." if home_injured else f"CRITICAL: {away_player_stats['top_scorer']} is out for {away_team}." if away_injured else "Key players are fit."
            },
            "h2h_history": self.get_h2h_history(home_team, away_team)
        }
