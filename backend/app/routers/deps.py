from fastapi import HTTPException

from ..ml.registry import registry
from ..services.data_store import get_store


def require_model():
    if registry.model is None:
        raise HTTPException(status_code=503, detail="Model is warming up, please retry in a few seconds.")
    return registry.model


def resolve_team_or_404(name: str) -> str:
    team = get_store().resolve_team(name)
    if team is None:
        raise HTTPException(status_code=404, detail=f"Unknown team '{name}'")
    return team
