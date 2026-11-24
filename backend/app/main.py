"""LaLiga Prediction Pro API."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from . import config
from .db import init_db
from .ml.registry import registry
from .routers import matches, players, predict, system, teams
from .services.data_store import get_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    get_store()
    registry.load_or_train()
    yield


app = FastAPI(title="LaLiga Prediction Pro API", version="2.0.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.netlify\.app|https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "healthy", "service": "LaLiga Prediction Pro API", "docs": "/docs"}


for r in (system.router, predict.router, teams.router, players.router, matches.router):
    app.include_router(r, prefix="/api")
