"""API tests against the bundled snapshot. External HTTP calls are blocked."""
import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory, monkeypatch_module):
    db = tmp_path_factory.mktemp("db") / "test.db"
    monkeypatch_module.setenv("DATABASE_URL", f"sqlite:///{db}")
    import importlib

    from app import config
    importlib.reload(config)
    from app import db as dbmod
    importlib.reload(dbmod)
    from app.services import football_api

    def no_network(*a, **k):
        raise RuntimeError("network disabled in tests")

    monkeypatch_module.setattr(football_api, "raw_get", no_network)
    from app.main import app
    with TestClient(app) as c:
        for _ in range(120):
            if c.get("/api/health").json()["model"] == "ready":
                break
            time.sleep(1)
        yield c


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def test_health(client):
    h = client.get("/api/health").json()
    assert h["model"] == "ready"
    assert h["data"]["matches"] > 700


def test_predict_is_deterministic_and_consistent(client):
    body = {"home_team": "Barcelona", "away_team": "Valladolid"}
    a = client.post("/api/predict", json=body).json()
    b = client.post("/api/predict", json=body).json()
    assert a["probabilities"] == b["probabilities"]
    p = a["probabilities"]
    assert abs(p["home_win"] + p["draw"] + p["away_win"] - 100) < 0.5
    assert p["home_win"] > p["away_win"]
    mk = a["markets"]
    assert mk["over_1_5"] >= mk["over_2_5"] >= mk["over_3_5"]
    assert a["scorelines"][0]["score"] == a["predicted_score"]


def test_predict_accepts_aliases(client):
    r = client.post("/api/predict", json={"home_team": "Atlético Madrid", "away_team": "Alavés"})
    assert r.status_code == 200
    assert r.json()["home_team"] == "Atletico Madrid"


@pytest.mark.parametrize("body", [
    {"home_team": "Barcelona", "away_team": "Barcelona"},
    {"home_team": "Nope FC", "away_team": "Barcelona"},
])
def test_predict_rejects_bad_input(client, body):
    assert client.post("/api/predict", json=body).status_code == 422


def test_fixtures_fall_back_without_network(client):
    r = client.get("/api/fixtures/upcoming")
    assert r.status_code == 200
    assert r.json()["source"] in ("unavailable", "stale-cache", "cache")


@pytest.mark.parametrize("path", [
    "/api/teams", "/api/standings", "/api/teams/Real%20Madrid/analysis", "/api/h2h?home=Barcelona&away=Real%20Madrid",
    "/api/players?limit=5", "/api/players/leaders", "/api/injuries", "/api/model/metrics", "/api/history",
    "/api/power-rankings", "/api/fixtures/results", "/api/fixtures/simulate-round",
])
def test_endpoints_ok(client, path):
    assert client.get(path).status_code == 200


def test_player_compare(client):
    players = client.get("/api/players?min_minutes=900&limit=2&sort=goals").json()["items"]
    a, b = players[0]["id"], players[1]["id"]
    r = client.get(f"/api/players/compare?a={a}&b={b}").json()
    assert r["a"]["id"] == a and len(r["radar"]) > 5
    assert client.get("/api/players/compare?a=1&b=2").status_code == 404
