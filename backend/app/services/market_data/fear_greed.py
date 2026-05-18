"""Fear & Greed Index via alternative.me — no API key required."""
import logging
from typing import Any, Dict

import httpx

from app.services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)
CACHE_KEY = "portai:market:fear_greed"
CACHE_TTL = 3600  # 1 hour


async def fetch_fear_greed() -> Dict[str, Any]:
    """Fetch current Fear & Greed Index. Cached 1 hour."""
    cached = await cache_get(CACHE_KEY)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.alternative.me/fng/?limit=7",
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            entries = data.get("data", [])
            current = entries[0] if entries else {}
            history = [
                {"value": int(e["value"]), "classification": e["value_classification"]}
                for e in entries[1:8]
            ]
            result = {
                "value": int(current.get("value", 50)),
                "classification": current.get("value_classification", "Neutral"),
                "timestamp": current.get("timestamp", ""),
                "history": history,
            }
    except Exception as exc:
        logger.error("Fear & Greed fetch failed: %s — using mock", exc)
        result = _mock_fear_greed()

    await cache_set(CACHE_KEY, result, ttl=CACHE_TTL)
    return result


def _mock_fear_greed() -> Dict[str, Any]:
    return {
        "value": 62,
        "classification": "Greed",
        "timestamp": "1715000000",
        "history": [
            {"value": 58, "classification": "Greed"},
            {"value": 55, "classification": "Neutral"},
            {"value": 61, "classification": "Greed"},
            {"value": 67, "classification": "Greed"},
            {"value": 71, "classification": "Extreme Greed"},
            {"value": 65, "classification": "Greed"},
            {"value": 60, "classification": "Greed"},
        ],
    }
