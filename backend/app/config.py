"""Central configuration. Everything is overridable through environment variables."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshot"
RAW_DIR = DATA_DIR / "raw"
MODELS_DIR = Path(os.getenv("MODELS_DIR", BACKEND_DIR / "models"))

# Read .env without mutating os.environ ordering problems (find_dotenv breaks on some interpreters).
_env_file = dotenv_values(BACKEND_DIR / ".env") if (BACKEND_DIR / ".env").exists() else {}


def _get(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or _env_file.get(name) or default


API_FOOTBALL_KEY: str | None = _get("API_FOOTBALL_KEY")
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
LEAGUE_ID = 140  # LaLiga

# The free API-Football plan exposes seasons 2022-2024 and a +/-1 day window for date queries.
TRAINING_SEASONS = [int(s) for s in (_get("TRAINING_SEASONS", "2022,2023,2024") or "").split(",") if s]

# Keep a safety margin under the 100 requests/day free-plan limit.
DAILY_REQUEST_BUDGET = int(_get("DAILY_REQUEST_BUDGET", "90") or 90)

DATABASE_URL = _get("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'predictions.db'}")

CORS_ORIGINS = [
    o.strip()
    for o in (_get(
        "CORS_ORIGINS",
        "http://localhost:8080,http://localhost:5173,http://127.0.0.1:8080,https://laligaprediction.netlify.app",
    ) or "").split(",")
    if o.strip()
]

# Cache time-to-live per resource (seconds).
TTL = {
    "live": 60,
    "today": 15 * 60,
    "standings": 6 * 3600,
    "injuries": 12 * 3600,
    "players": 24 * 3600,
    "finished": 10 * 365 * 24 * 3600,
}
