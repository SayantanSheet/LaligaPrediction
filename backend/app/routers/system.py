from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from ..db import MatchPrediction, get_db
from ..ml.registry import registry
from ..services import football_api
from ..services.data_store import get_store

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    store = get_store()
    return {
        "status": "ok" if registry.ready else registry.status,
        "model": registry.status, "model_error": registry.error,
        "data": {"matches": len(store.matches), "players": len(store.players), "data_as_of": store.data_as_of,
                 "latest_season": store.latest_season, "player_season": store.players_season},
        "api_quota": football_api.quota_status(),
    }


@router.get("/model/metrics")
def model_metrics():
    m = registry.model
    if m is None:
        return {"status": registry.status}
    return {"status": registry.status, **m.metrics}


@router.get("/history")
def history(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    rows = db.query(MatchPrediction).order_by(MatchPrediction.created_at.desc()).limit(limit).all()
    total = db.query(MatchPrediction).count()
    items = [{
        "id": r.id, "home_team": r.home_team, "away_team": r.away_team, "predicted_score": r.predicted_score,
        "predicted_outcome": r.predicted_outcome,
        "home_win_prob": r.home_win_prob, "draw_prob": r.draw_prob, "away_win_prob": r.away_win_prob,
        # legacy rows stored confidence as a percentage
        "confidence": (r.confidence / 100 if r.confidence and r.confidence > 1 else r.confidence),
        "expected_goals_home": r.expected_goals_home, "expected_goals_away": r.expected_goals_away,
        "actual_score": r.actual_score,
        "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
    } for r in rows]
    return {"total": total, "items": items}


@router.post("/refresh")
def refresh(background: BackgroundTasks):
    """Reload the snapshot from disk and retrain in the background (non-blocking)."""
    def job():
        get_store().reload()
        from ..services.prediction import _predict_cached
        _predict_cached.cache_clear()
        registry.retrain_async()
    background.add_task(job)
    return {"status": "scheduled"}
