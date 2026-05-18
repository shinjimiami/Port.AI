"""Cryptocurrency data via CoinGecko API — with Redis cache."""
import logging
from typing import Dict, List, Optional

import httpx

from app.config import settings
from app.schemas.market import CryptoQuote
from app.services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
CACHE_KEY = "portai:market:crypto"

CRYPTO_TIERS = {
    "large_cap": ["bitcoin", "ethereum", "binancecoin", "solana", "ripple"],
    "mid_cap":   ["cardano", "avalanche-2", "chainlink", "polkadot", "polygon"],
    "defi":      ["uniswap", "aave", "compound-governance-token", "maker"],
    "layer2":    ["optimism", "arbitrum"],
}


async def fetch_crypto(top_n: int = 50) -> Dict[str, List[dict]]:
    """Return top-N coins grouped by tier. Results cached for 15 min."""
    cached = await cache_get(CACHE_KEY)
    if cached:
        logger.debug("Crypto cache hit")
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
                    "per_page": top_n,
                    "page": 1,
                    "price_change_percentage": "1h,24h,7d,30d",
                    "sparkline": "false",
                },
                timeout=15,
            )
            resp.raise_for_status()
            raw: List[dict] = resp.json()
    except Exception as exc:
        logger.error("CoinGecko fetch failed: %s — using mock data", exc)
        data = _mock_crypto()
        await cache_set(CACHE_KEY, data)
        return data

    by_tier: Dict[str, List[dict]] = {}
    for coin in raw:
        try:
            pcp = coin.get("price_change_percentage_24h_in_currency") or coin.get("price_change_percentage_24h")
            q = CryptoQuote(
                id=coin["id"],
                symbol=coin["symbol"].upper(),
                name=coin["name"],
                price_usd=float(coin.get("current_price") or 0),
                change_pct_1d=float(pcp or 0),
                change_pct_7d=float(coin.get("price_change_percentage_7d_in_currency") or 0),
                change_pct_30d=float(coin.get("price_change_percentage_30d_in_currency") or 0),
                market_cap_usd=float(coin.get("market_cap") or 0),
                volume_24h_usd=float(coin.get("total_volume") or 0),
                rank=coin.get("market_cap_rank"),
            )
            tier = _get_tier(q.id)
            by_tier.setdefault(tier, []).append(q.model_dump())
        except Exception as exc:
            logger.warning("Skipping coin %s: %s", coin.get("id"), exc)

    result = by_tier if by_tier else _mock_crypto()
    await cache_set(CACHE_KEY, result)
    return result


def _get_tier(coin_id: str) -> str:
    for tier, ids in CRYPTO_TIERS.items():
        if coin_id in ids:
            return tier
    return "other"


def _mock_crypto() -> Dict[str, List[dict]]:
    return {
        "large_cap": [
            {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "price_usd": 67500.0,
             "change_pct_1d": 1.2, "change_pct_7d": 4.5, "change_pct_30d": 12.3,
             "market_cap_usd": 1_330_000_000_000, "rank": 1},
            {"id": "ethereum", "symbol": "ETH", "name": "Ethereum", "price_usd": 3550.0,
             "change_pct_1d": 0.8, "change_pct_7d": 3.1, "change_pct_30d": 8.7,
             "market_cap_usd": 427_000_000_000, "rank": 2},
            {"id": "solana", "symbol": "SOL", "name": "Solana", "price_usd": 178.0,
             "change_pct_1d": 2.1, "change_pct_7d": 9.4, "change_pct_30d": 22.1,
             "market_cap_usd": 82_000_000_000, "rank": 5},
        ],
        "mid_cap": [
            {"id": "chainlink", "symbol": "LINK", "name": "Chainlink", "price_usd": 18.50,
             "change_pct_1d": 1.5, "change_pct_7d": 6.2, "change_pct_30d": 15.0,
             "market_cap_usd": 11_000_000_000, "rank": 14},
            {"id": "cardano", "symbol": "ADA", "name": "Cardano", "price_usd": 0.45,
             "change_pct_1d": 0.5, "change_pct_7d": 2.8, "change_pct_30d": 7.2,
             "market_cap_usd": 16_000_000_000, "rank": 10},
        ],
        "defi": [
            {"id": "uniswap", "symbol": "UNI", "name": "Uniswap", "price_usd": 11.20,
             "change_pct_1d": 0.9, "change_pct_7d": 4.1, "change_pct_30d": 9.5,
             "market_cap_usd": 6_700_000_000, "rank": 22},
        ],
        "layer2": [
            {"id": "arbitrum", "symbol": "ARB", "name": "Arbitrum", "price_usd": 1.05,
             "change_pct_1d": 1.3, "change_pct_7d": 5.8, "change_pct_30d": 14.2,
             "market_cap_usd": 3_200_000_000, "rank": 35},
        ],
    }
