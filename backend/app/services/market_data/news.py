"""Market news via NewsAPI.org with mock fallback."""
import logging
from typing import Any, Dict, List

import httpx

from app.config import settings
from app.services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)
CACHE_KEY = "portai:market:news"
CACHE_TTL = 900  # 15 min
NEWSAPI_BASE = "https://newsapi.org/v2"


async def fetch_market_news(page_size: int = 10) -> List[Dict[str, Any]]:
    """Fetch latest market news. Cached 15 min."""
    cached = await cache_get(CACHE_KEY)
    if cached:
        return cached

    if not settings.NEWSAPI_KEY:
        logger.warning("NEWSAPI_KEY not set — returning mock news")
        data = _mock_news()
        await cache_set(CACHE_KEY, data, ttl=CACHE_TTL)
        return data

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{NEWSAPI_BASE}/top-headlines",
                params={
                    "apiKey": settings.NEWSAPI_KEY,
                    "category": "business",
                    "language": "en",
                    "pageSize": page_size,
                },
                timeout=10,
            )
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            result = [
                {
                    "title": a.get("title", ""),
                    "description": a.get("description", ""),
                    "url": a.get("url", ""),
                    "source": a.get("source", {}).get("name", ""),
                    "published_at": a.get("publishedAt", ""),
                    "image_url": a.get("urlToImage"),
                }
                for a in articles
                if a.get("title") and "[Removed]" not in a.get("title", "")
            ]
            if not result:
                result = _mock_news()
    except Exception as exc:
        logger.error("NewsAPI fetch failed: %s — using mock", exc)
        result = _mock_news()

    await cache_set(CACHE_KEY, result, ttl=CACHE_TTL)
    return result


def _mock_news() -> List[Dict[str, Any]]:
    return [
        {
            "title": "Fed Signals Rates May Stay Higher for Longer Amid Sticky Inflation",
            "description": "Federal Reserve officials hinted at maintaining elevated interest rates as inflation proves more stubborn than expected.",
            "url": "#",
            "source": "Reuters",
            "published_at": "2025-05-10T08:00:00Z",
            "image_url": None,
        },
        {
            "title": "S&P 500 Hits New Record as Tech Earnings Beat Expectations",
            "description": "US equity markets rallied as strong earnings from major technology companies lifted sentiment across sectors.",
            "url": "#",
            "source": "Bloomberg",
            "published_at": "2025-05-10T07:30:00Z",
            "image_url": None,
        },
        {
            "title": "Bitcoin Surpasses $70,000 Amid Institutional Accumulation",
            "description": "Bitcoin reached a new year-to-date high as institutional investors continue to build long positions.",
            "url": "#",
            "source": "CoinDesk",
            "published_at": "2025-05-10T06:45:00Z",
            "image_url": None,
        },
        {
            "title": "IDX Composite Gains 1.2% on Foreign Capital Inflows",
            "description": "The Jakarta Composite Index rose on the back of strong foreign buying in banking and commodity stocks.",
            "url": "#",
            "source": "Bisnis Indonesia",
            "published_at": "2025-05-10T05:00:00Z",
            "image_url": None,
        },
        {
            "title": "Oil Prices Stabilize After OPEC+ Maintains Production Cuts",
            "description": "Crude oil prices found support after OPEC+ members confirmed commitment to production cuts through year-end.",
            "url": "#",
            "source": "Financial Times",
            "published_at": "2025-05-09T18:00:00Z",
            "image_url": None,
        },
        {
            "title": "Emerging Markets Rally as Dollar Weakens on Rate Cut Expectations",
            "description": "Asian and emerging market equities gained ground as the US dollar softened following softer-than-expected jobs data.",
            "url": "#",
            "source": "Wall Street Journal",
            "published_at": "2025-05-09T15:30:00Z",
            "image_url": None,
        },
    ]
