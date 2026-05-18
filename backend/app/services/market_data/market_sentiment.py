"""Intraday market sentiment from live crypto market data."""
import logging
import math
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

from app.config import settings
from app.services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
CACHE_KEY = "portai:market:live_sentiment"
CACHE_TTL = 60
COIN_SAMPLE_SIZE = 30


async def fetch_market_sentiment() -> Dict[str, Any]:
    """Fetch and score intraday market sentiment. Cached for 60 seconds."""
    cached = await cache_get(CACHE_KEY)
    if cached:
        return cached

    headers = {}
    if settings.COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = settings.COINGECKO_API_KEY

    try:
        async with httpx.AsyncClient(headers=headers) as client:
            resp = await client.get(
                f"{COINGECKO_BASE}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": COIN_SAMPLE_SIZE,
                    "page": 1,
                    "price_change_percentage": "1h,24h,7d",
                    "sparkline": "false",
                },
                timeout=12,
            )
            resp.raise_for_status()
            result = calculate_market_sentiment(resp.json())
    except Exception as exc:
        logger.error("Live market sentiment fetch failed: %s - using mock", exc)
        result = _mock_market_sentiment()

    await cache_set(CACHE_KEY, result, ttl=CACHE_TTL)
    return result


def calculate_market_sentiment(raw_coins: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate a 0-100 sentiment score from CoinGecko market snapshots."""
    coins = [_normalize_coin(c) for c in raw_coins]
    coins = [c for c in coins if c["market_cap"] > 0]
    if not coins:
        raise ValueError("no usable market data")

    weights = _market_cap_weights(coins)
    weighted_1h = _weighted_average([c["change_1h"] for c in coins], weights)
    weighted_24h = _weighted_average([c["change_24h"] for c in coins], weights)
    weighted_7d = _weighted_average([c["change_7d"] for c in coins], weights)
    blended_momentum = (weighted_1h * 0.45) + (weighted_24h * 0.35) + (weighted_7d * 0.20)

    momentum_score = _pct_to_score(blended_momentum, scale=8.0)
    short_momentum_score = _pct_to_score(weighted_1h, scale=2.5)
    breadth_pct = sum(1 for c in coins if c["change_24h"] > 0) / len(coins) * 100
    breadth_score = _clamp(breadth_pct)
    volatility = statistics.pstdev([c["change_24h"] for c in coins]) if len(coins) > 1 else 0.0
    stability_score = _clamp(100 - (volatility * 6))

    score = round(
        (momentum_score * 0.35)
        + (short_momentum_score * 0.25)
        + (breadth_score * 0.25)
        + (stability_score * 0.15)
    )

    result = {
        "value": int(_clamp(score)),
        "classification": _classification(score),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "CoinGecko coins/markets",
        "is_live": True,
        "is_mock": False,
        "refresh_seconds": CACHE_TTL,
        "sample_size": len(coins),
        "components": [
            {
                "key": "blended_momentum",
                "name": "Blended momentum",
                "score": round(momentum_score),
                "value": round(blended_momentum, 2),
                "label": f"{_fmt_pct(blended_momentum)} weighted 1h/24h/7d",
            },
            {
                "key": "short_momentum",
                "name": "1h momentum",
                "score": round(short_momentum_score),
                "value": round(weighted_1h, 2),
                "label": f"{_fmt_pct(weighted_1h)} market-cap weighted",
            },
            {
                "key": "breadth",
                "name": "Market breadth",
                "score": round(breadth_score),
                "value": round(breadth_pct, 2),
                "label": f"{round(breadth_pct)}% of tracked coins up 24h",
            },
            {
                "key": "stability",
                "name": "Volatility stress",
                "score": round(stability_score),
                "value": round(volatility, 2),
                "label": f"{round(volatility, 2)}% 24h dispersion",
            },
        ],
        "drivers": _drivers(coins),
    }
    return result


def _normalize_coin(coin: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "symbol": str(coin.get("symbol") or "").upper(),
        "name": str(coin.get("name") or ""),
        "market_cap": _to_float(coin.get("market_cap")),
        "change_1h": _to_float(coin.get("price_change_percentage_1h_in_currency")),
        "change_24h": _to_float(
            coin.get("price_change_percentage_24h_in_currency")
            or coin.get("price_change_percentage_24h")
        ),
        "change_7d": _to_float(coin.get("price_change_percentage_7d_in_currency")),
        "rank": coin.get("market_cap_rank") or 9999,
    }


def _market_cap_weights(coins: List[Dict[str, Any]]) -> List[float]:
    total = sum(c["market_cap"] for c in coins)
    if total <= 0:
        return [1 / len(coins)] * len(coins)
    return [c["market_cap"] / total for c in coins]


def _weighted_average(values: List[float], weights: List[float]) -> float:
    return sum(value * weight for value, weight in zip(values, weights))


def _pct_to_score(value: float, scale: float) -> float:
    return _clamp(50 + (50 * math.tanh(value / scale)))


def _classification(score: float) -> str:
    if score <= 20:
        return "Strongly Bearish"
    if score <= 40:
        return "Bearish"
    if score < 60:
        return "Neutral"
    if score < 80:
        return "Bullish"
    return "Strongly Bullish"


def _drivers(coins: List[Dict[str, Any]]) -> List[str]:
    majors = sorted(coins, key=lambda c: c["rank"])[:5]
    return [
        f"{c['symbol']} 1h {_fmt_pct(c['change_1h'])}, 24h {_fmt_pct(c['change_24h'])}"
        for c in majors
        if c["symbol"]
    ]


def _to_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _fmt_pct(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def _clamp(value: float, min_value: float = 0, max_value: float = 100) -> float:
    return max(min_value, min(max_value, value))


def _mock_market_sentiment() -> Dict[str, Any]:
    return {
        "value": 58,
        "classification": "Neutral",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "mock",
        "is_live": False,
        "is_mock": True,
        "refresh_seconds": CACHE_TTL,
        "sample_size": 0,
        "components": [
            {
                "key": "blended_momentum",
                "name": "Blended momentum",
                "score": 61,
                "value": 1.8,
                "label": "+1.80% weighted 1h/24h/7d",
            },
            {
                "key": "short_momentum",
                "name": "1h momentum",
                "score": 56,
                "value": 0.3,
                "label": "+0.30% market-cap weighted",
            },
            {
                "key": "breadth",
                "name": "Market breadth",
                "score": 62,
                "value": 62,
                "label": "62% of tracked coins up 24h",
            },
            {
                "key": "stability",
                "name": "Volatility stress",
                "score": 48,
                "value": 8.7,
                "label": "8.7% 24h dispersion",
            },
        ],
        "drivers": [
            "BTC 1h +0.20%, 24h +1.10%",
            "ETH 1h +0.10%, 24h +0.80%",
        ],
    }
