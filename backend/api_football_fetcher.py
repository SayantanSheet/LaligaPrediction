import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

class APIFootballFetcher:
    BASE_URL = "https://v3.football.api-sports.io"
    HEADERS = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': os.getenv("API_FOOTBALL_KEY")
    }

    def __init__(self, api_key=None):
        if api_key:
            self.HEADERS['x-rapidapi-key'] = api_key
        
        if not self.HEADERS['x-rapidapi-key']:
            print("[WARN] API_FOOTBALL_KEY not found in environment variables.")

    def fetch_fixtures(self, league_id=140, season=2023):
        """Fetch fixtures for a specific league and season."""
        url = f"{self.BASE_URL}/fixtures"
        params = {
            "league": league_id,
            "season": season
        }
        
        try:
            response = requests.get(url, headers=self.HEADERS, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("errors"):
                print(f"[ERROR] API-Football Errors: {data['errors']}")
                return []
                
            return data.get("response", [])
        except Exception as e:
            print(f"[ERROR] Failed to fetch fixtures: {e}")
            return []

    def format_to_canonical(self, fixtures):
        """Format API-Football fixtures to the format expected by the models."""
        formatted = []
        for f in fixtures:
            # Only include finished matches
            if f['fixture']['status']['short'] != 'FT':
                continue
                
            formatted.append({
                "id": f['fixture']['id'],
                "homeTeam": f['teams']['home']['name'],
                "awayTeam": f['teams']['away']['name'],
                "homeScore": f['goals']['home'],
                "awayScore": f['goals']['away'],
                "date": f['fixture']['date'][:10], # YYYY-MM-DD
                "season": f['league']['season']
            })
        return formatted

if __name__ == "__main__":
    fetcher = APIFootballFetcher()
    # Test fetch (this will likely fail without a valid key, but handles errors)
    fixtures = fetcher.fetch_fixtures(league_id=140, season=2023)
    formatted = fetcher.format_to_canonical(fixtures)
    print(f"Fetched and formatted {len(formatted)} matches.")