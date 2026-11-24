"""SQLite persistence: prediction history, API response cache and request quota."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class MatchPrediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    home_team = Column(String, index=True)
    away_team = Column(String, index=True)
    predicted_score = Column(String)
    predicted_outcome = Column(String)  # "H" | "D" | "A"
    home_win_prob = Column(Float)
    draw_prob = Column(Float)
    away_win_prob = Column(Float)
    confidence = Column(Float)  # probability of the predicted outcome, 0-1
    expected_goals_home = Column(Float)
    expected_goals_away = Column(Float)
    fixture_id = Column(Integer, nullable=True, index=True)
    actual_score = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class ApiCache(Base):
    __tablename__ = "api_cache"

    key = Column(String, primary_key=True)
    payload = Column(Text)
    fetched_at = Column(DateTime, default=utcnow)


class ApiQuota(Base):
    __tablename__ = "api_quota"

    day = Column(String, primary_key=True)  # YYYY-MM-DD (UTC)
    used = Column(Integer, default=0)


_LEGACY_COLUMNS = {
    "predicted_outcome": "VARCHAR",
    "expected_goals_home": "FLOAT",
    "expected_goals_away": "FLOAT",
    "fixture_id": "INTEGER",
    "actual_score": "VARCHAR",
}


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    # Lightweight migration for databases created by the previous version of the app.
    if DATABASE_URL.startswith("sqlite"):
        with engine.begin() as conn:
            cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(predictions)")}
            for name, typ in _LEGACY_COLUMNS.items():
                if name not in cols:
                    conn.exec_driver_sql(f"ALTER TABLE predictions ADD COLUMN {name} {typ}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
