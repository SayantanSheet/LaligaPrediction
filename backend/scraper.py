import json
import os
from api_football_fetcher import APIFootballFetcher

def main():
    print("Fetching Real Historical LaLiga Match Data from API-Football...")
    
    fetcher = APIFootballFetcher()
    
    # Fetch data for the last few seasons to have a robust dataset
    all_formatted_matches = []
    for season in [2022, 2023]:
        print(f"Fetching season {season}...")
        fixtures = fetcher.fetch_fixtures(league_id=140, season=season)
        formatted = fetcher.format_to_canonical(fixtures)
        all_formatted_matches.extend(formatted)
        print(f"Found {len(formatted)} finished matches in season {season}.")

    if not all_formatted_matches:
        print("[ERROR] No matches were fetched. Check your API key and connection.")
        return

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    data_dir = os.path.join(project_root, 'src', 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    data_path = os.path.join(data_dir, 'matches-all-seasons.json')
    
    # Sort by date
    all_formatted_matches.sort(key=lambda x: x["date"])

    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(all_formatted_matches, f, indent=2)
    
    print(f"Update complete! Successfully saved {len(all_formatted_matches)} historical matches to {data_path}")

if __name__ == "__main__":
    main()
