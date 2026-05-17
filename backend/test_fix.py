import os
import sys
from predictor import PredictionEngine

# Mimic the environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    engine = PredictionEngine()
    teams = engine.get_teams()
    if len(teams) >= 2:
        home, away = teams[0], teams[1]
        print(f"Predicting {home} vs {away}...")
        result = engine.predict_match(home, away)
        
        # Check for properties needed by frontend
        print(f"Confidence: {result['confidence']}%")
        print(f"Home Lambda: {result['performance_analysis']['home'].get('lambda')}")
        print(f"Comparison Variance: {result['comparison'].get('variance')}%")
        
        if result['performance_analysis']['home'].get('lambda') is not None and \
           result['comparison'].get('variance') is not None:
            print("Success! All frontend properties are present.")
        else:
            print("Failure! Some properties are missing.")
    else:
        print("Not enough teams to test.")
except Exception as e:
    import traceback
    traceback.print_exc()
