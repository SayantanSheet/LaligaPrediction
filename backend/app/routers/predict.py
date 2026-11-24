from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..db import MatchPrediction, get_db
from ..services import prediction
from ..services.data_store import get_store
from .deps import require_model

router = APIRouter(tags=["predictions"])


class PredictionRequest(BaseModel):
    home_team: str = Field(..., min_length=2, max_length=60)
    away_team: str = Field(..., min_length=2, max_length=60)
    use_availability: bool = True
    fixture_id: int | None = None

    @field_validator("home_team", "away_team")
    @classmethod
    def strip(cls, v: str) -> str:
        return v.strip()


@router.post("/predict")
def predict(req: PredictionRequest, db: Session = Depends(get_db), _=Depends(require_model)):
    store = get_store()
    home, away = store.resolve_team(req.home_team), store.resolve_team(req.away_team)
    unknown = [n for n, t in ((req.home_team, home), (req.away_team, away)) if t is None]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown team(s): {', '.join(unknown)}")
    if home == away:
        raise HTTPException(status_code=422, detail="Home and away team must be different")

    result = prediction.predict(home, away, req.use_availability)
    p = result["probabilities"]
    db.add(MatchPrediction(
        home_team=home, away_team=away, predicted_score=result["predicted_score"],
        predicted_outcome=result["predicted_outcome"],
        home_win_prob=p["home_win"] / 100, draw_prob=p["draw"] / 100, away_win_prob=p["away_win"] / 100,
        confidence=result["confidence"] / 100,
        expected_goals_home=result["expected_goals"]["home"], expected_goals_away=result["expected_goals"]["away"],
        fixture_id=req.fixture_id,
    ))
    db.commit()
    return result
