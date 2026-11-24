"""API-Football client with a SQLite TTL cache and a daily request budget.

Every call goes: fresh cache hit -> live request (if budget allows) -> stale cache -> None.
Callers fall back to the bundled snapshot when this returns None.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import threading
from dataclasses import dataclass
from typing import Any

import httpx

from .. import config
from ..db import ApiCache, ApiQuota, SessionLocal, utcnow

log = logging.getLogger("football_api")
_lock = threading.Lock()


@dataclass
class ApiResult:
    data: Any
    source: str  # "live" | "cache" | "stale-cache"
    fetched_at: dt.datetime


class QuotaExceeded(RuntimeError):
    pass


def _cache_key(endpoint: str, params: dict) -> str:
    return endpoint + "?" + "&".join(f"{k}={params[k]}" for k in sorted(params))


def quota_status() -> dict:
    today = utcnow().strftime("%Y-%m-%d")
    with SessionLocal() as db:
        row = db.get(ApiQuota, today)
        used = row.used if row else 0
    return {"day": today, "used": used, "budget": config.DAILY_REQUEST_BUDGET,
            "remaining": max(0, config.DAILY_REQUEST_BUDGET - used),
            "configured": bool(config.API_FOOTBALL_KEY)}


def _consume_quota() -> None:
    today = utcnow().strftime("%Y-%m-%d")
    with _lock, SessionLocal() as db:
        row = db.get(ApiQuota, today)
        if row is None:
            row = ApiQuota(day=today, used=0)
            db.add(row)
        if row.used >= config.DAILY_REQUEST_BUDGET:
            raise QuotaExceeded(f"Daily API budget of {config.DAILY_REQUEST_BUDGET} reached")
        row.used += 1
        db.commit()


def _sync_quota_from_headers(headers) -> None:
    """The account quota is shared with other clients (scripts, other deployments). API-Football reports
    the remaining daily requests in a header; never let our local counter be more optimistic than that."""
    try:
        limit = int(headers.get("x-ratelimit-requests-limit"))
        remaining = int(headers.get("x-ratelimit-requests-remaining"))
    except (TypeError, ValueError):
        return
    account_used = limit - remaining
    today = utcnow().strftime("%Y-%m-%d")
    with _lock, SessionLocal() as db:
        row = db.get(ApiQuota, today) or ApiQuota(day=today, used=0)
        row.used = max(row.used or 0, account_used)
        db.merge(row)
        db.commit()


def _read_cache(key: str) -> ApiCache | None:
    with SessionLocal() as db:
        return db.get(ApiCache, key)


def _write_cache(key: str, payload: Any) -> None:
    with SessionLocal() as db:
        row = db.get(ApiCache, key)
        if row is None:
            row = ApiCache(key=key)
            db.add(row)
        row.payload = json.dumps(payload)
        row.fetched_at = utcnow()
        db.commit()


def raw_get(endpoint: str, params: dict, timeout: float = 30.0) -> dict:
    """Perform one real HTTP request (counts against the quota). Raises on API errors."""
    if not config.API_FOOTBALL_KEY:
        raise RuntimeError("API_FOOTBALL_KEY is not configured")
    _consume_quota()
    resp = httpx.get(
        f"{config.API_FOOTBALL_BASE}/{endpoint}",
        params=params,
        headers={"x-apisports-key": config.API_FOOTBALL_KEY},
        timeout=timeout,
    )
    resp.raise_for_status()
    _sync_quota_from_headers(resp.headers)
    body = resp.json()
    errors = body.get("errors")
    if errors:
        raise RuntimeError(f"API-Football error: {errors}")
    return body


def get(endpoint: str, params: dict, ttl: int) -> ApiResult | None:
    key = _cache_key(endpoint, params)
    cached = _read_cache(key)
    now = utcnow()
    if cached and (now - cached.fetched_at).total_seconds() < ttl:
        return ApiResult(json.loads(cached.payload), "cache", cached.fetched_at)
    try:
        body = raw_get(endpoint, params)
        data = body.get("response")
        _write_cache(key, data)
        return ApiResult(data, "live", now)
    except Exception as exc:  # network, quota, plan restrictions
        log.warning("API-Football %s failed: %s", key, exc)
        if cached:
            return ApiResult(json.loads(cached.payload), "stale-cache", cached.fetched_at)
        return None
