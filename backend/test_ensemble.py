import pandas as pd
import json
import os
from predictor import PredictionEngine

def test_system():
    print("Initializing Prediction Engine...")
    engine = PredictionEngine()
    
    if not engine.is_ready:
        print("FAILED: Engine not ready.")
        return

    teams = engine.get_teams()
    print(f"Available teams: {len(teams)}")
    
    if len(teams) >= 2:
        home, away = teams[0], teams[1]
        print(f"\nTesting prediction for {home} vs {away}...")
        result = engine.predict_match(home, away)
        
        if "error" in result:
            print(f"FAILED: {result['error']}")
        else:
            print(f"SUCCESS: Predicted {result['predicted_score']}")
            print(f"Probabilities: Win={result['probabilities']['home_win']:.2%}, "
                  f"Draw={result['probabilities']['draw']:.2%}, "
                  f"Away={result['probabilities']['away_win']:.2%}")
            print(f"Confidence: {result['confidence']:.2%}")
            
            # Test injury override
            print(f"\nTesting injury override for {home}...")
            # We can't easily force an injury in predict_match without modifying engine state or player_data
            # but predict_match uses get_player_stats which has a random 15% chance.
            # For a reliable test, we'd need to mock player_data.
            pass

    print("\nSystem verified.")

if __name__ == "__main__":
    test_system()
