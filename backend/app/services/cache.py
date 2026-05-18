"""
Thin Redis wrapper.

Usage (async):
    data = await cache_get("key")
    await cache_set("key", data, ttl=900)

Usage (sync — for Celery workers):
    data = sync_cache_get("key")
    sync_cache_set("key", data, ttl=900)
"""
import json
import logging
from typing import Any, Optional

import redis as sync_redis
import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# ── Async client (FastAPI / LangGraph) ───────────────────────────────────────

_async_client: Optional[aioredis.Redis] = None


def _async_redis() -> aioredis.Redis:
    global _async_client
    if _async_client is None:
        _async_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _async_client


async def cache_get(key: str) -> Optional[Any]:
    try:
        raw = await _async_redis().get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("cache_get(%s) failed: %s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl: int = settings.MARKET_CACHE_TTL_SECONDS) -> None:
    try:
        await _async_redis().setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.warning("cache_set(%s) failed: %s", key, exc)


async def cache_delete(key: str) -> None:
    try:
        await _async_redis().delete(key)
    except Exception as exc:
        logger.warning("cache_delete(%s) failed: %s", key, exc)


# ── Sync client (Celery workers) ──────────────────────────────────────────────

_sync_client: Optional[sync_redis.Redis] = None


def _sync_redis() -> sync_redis.Redis:
    global _sync_client
    if _sync_client is None:
        _sync_client = sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _sync_client


def sync_cache_get(key: str) -> Optional[Any]:
    try:
        raw = _sync_redis().get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("sync_cache_get(%s) failed: %s", key, exc)
        return None


def sync_cache_set(key: str, value: Any, ttl: int = settings.MARKET_CACHE_TTL_SECONDS) -> None:
    try:
        _sync_redis().setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.warning("sync_cache_set(%s) failed: %s", key, exc)


# ── Progress helpers (portfolio pipeline) ────────────────────────────────────

PROGRESS_TTL = 3600  # 1 hour


async def publish_progress(portfolio_id: int, node: str, message: str = "") -> None:
    """Write current pipeline node to Redis for SSE consumers."""
    key = f"portai:portfolio:{portfolio_id}:progress"
    payload = json.dumps({"node": node, "message": message})
    try:
        await _async_redis().setex(key, PROGRESS_TTL, payload)
        # Also publish to channel for real-time consumers
        await _async_redis().publish(f"portai:progress:{portfolio_id}", payload)
    except Exception as exc:
        logger.warning("publish_progress failed: %s", exc)


def sync_publish_progress(portfolio_id: int, node: str, message: str = "") -> None:
    """Sync version used inside Celery tasks."""
    key = f"portai:portfolio:{portfolio_id}:progress"
    payload = json.dumps({"node": node, "message": message})
    try:
        _sync_redis().setex(key, PROGRESS_TTL, payload)
        _sync_redis().publish(f"portai:progress:{portfolio_id}", payload)
    except Exception as exc:
        logger.warning("sync_publish_progress failed: %s", exc)


async def get_progress(portfolio_id: int) -> Optional[dict]:
    key = f"portai:portfolio:{portfolio_id}:progress"
    return await cache_get(key)
