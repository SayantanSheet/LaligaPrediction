"""In-memory data store backed by the bundled snapshot (data/snapshot/*.json).

The snapshot is produced by scripts/build_snapshot.py from API-Football. Everything that
needs historical data (models, team analysis, players, injuries) reads from here, so the
app works offline and when the free API quota is exhausted.
"""
from __future__ import annotations

import json
import threading
import unicodedata
from functools import cached_property
from pathlib import Path

import pandas as pd

from .. import config

_ALIASES = {
    "atletico de madrid": "Atletico Madrid",
    "atl. madrid": "Atletico Madrid",
    "granada": "Granada CF",
    "deportivo alaves": "Alaves",
    "real valladolid": "Valladolid",
    "rcd mallorca": "Mallorca",
    "rcd espanyol": "Espanyol",
    "ud las palmas": "Las Palmas",
    "cd leganes": "Leganes",
    "girona fc": "Girona",
    "celta de vigo": "Celta Vigo",
    "rc celta": "Celta Vigo",
    "ca osasuna": "Osasuna",
    "fc barcelona": "Barcelona",
    "sevilla fc": "Sevilla",
    "villarreal cf": "Villarreal",
    "valencia cf": "Valencia",
    "getafe cf": "Getafe",
    "real oviedo": "Oviedo",
    "levante ud": "Levante",
}


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def canonical_team(name: str) -> str:
    """Normalise whitespace/accents and map known aliases to the dataset's canonical team name."""
    clean = " ".join(_strip_accents(str(name)).replace("\n", " ").split()).strip()
    return _ALIASES.get(clean.lower(), clean)


def _load(name: str, default):
    path = config.SNAPSHOT_DIR / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


class DataStore:
    """Read-mostly container; `reload()` swaps everything atomically after a refresh."""

    def __init__(self, snapshot_dir: Path | None = None):
        self._lock = threading.Lock()
        self.snapshot_dir = snapshot_dir or config.SNAPSHOT_DIR
        self.reload()

    def reload(self) -> None:
        with self._lock:
            for attr in ("matches_df", "team_index"):
                self.__dict__.pop(attr, None)
            self.matches: list[dict] = _load("matches.json", [])
            self.teams_meta: dict[str, dict] = {t["name"]: t for t in _load("teams.json", [])}
            self.standings: dict = _load("standings.json", {"season": None, "table": []})
            p = _load("players.json", {"season": None, "players": []})
            self.players: list[dict] = p["players"]
            self.players_season = p["season"]
            self.players_by_id = {pl["id"]: pl for pl in self.players}
            inj = _load("injuries.json", {"season": None, "injuries": []})
            self.injuries: list[dict] = inj["injuries"]
            self.version = f"{len(self.matches)}-{self.matches[-1]['date'] if self.matches else 'none'}"

    @cached_property
    def matches_df(self) -> pd.DataFrame:
        df = pd.DataFrame(self.matches)
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values(["date", "id"]).reset_index(drop=True)

    @property
    def latest_season(self) -> int | None:
        return int(self.matches_df["season"].max()) if not self.matches_df.empty else None

    @property
    def data_as_of(self) -> str | None:
        return self.matches[-1]["date"] if self.matches else None

    def all_teams(self) -> list[str]:
        if self.matches_df.empty:
            return []
        return sorted(set(self.matches_df["homeTeam"]) | set(self.matches_df["awayTeam"]))

    def current_teams(self) -> list[str]:
        """Teams that played in the most recent season (the ones that make sense to predict)."""
        df = self.matches_df
        if df.empty:
            return []
        last = df[df["season"] == df["season"].max()]
        return sorted(set(last["homeTeam"]) | set(last["awayTeam"]))

    def resolve_team(self, name: str) -> str | None:
        name = canonical_team(name)
        teams = self.all_teams()
        if name in teams:
            return name
        lower = {t.lower(): t for t in teams}
        return lower.get(name.lower())

    def team_meta(self, team: str) -> dict:
        return self.teams_meta.get(team, {"name": team, "logo": None, "id": None})


_store: DataStore | None = None


def get_store() -> DataStore:
    global _store
    if _store is None:
        _store = DataStore()
    return _store
