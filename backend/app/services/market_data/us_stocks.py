"""US stock data via Alpha Vantage API — with Redis cache."""
import logging
from typing import Dict, List, Optional

import httpx

from app.config import settings
from app.schemas.market import StockQuote
from app.services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

BASE_URL = "https://www.alphavantage.co/query"
CACHE_KEY = "portai:market:us_stocks"

SECTOR_TICKERS: Dict[str, List[str]] = {
    "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
    "Healthcare":  ["JNJ", "UNH", "PFE", "ABBV", "MRK"],
    "Finance":     ["JPM", "BAC", "WFC", "GS", "MS"],
    "Consumer":    ["AMZN", "TSLA", "NKE", "MCD", "SBUX"],
    "Energy":      ["XOM", "CVX", "SLB", "COP", "EOG"],
    "Industrial":  ["CAT", "HON", "GE", "MMM", "UPS"],
}

ALL_TICKERS = [t for tickers in SECTOR_TICKERS.values() for t in tickers]


async def _fetch_quote(ticker: str, client: httpx.AsyncClient) -> Optional[StockQuote]:
    try:
        resp = await client.get(
            BASE_URL,
            params={
                "function": "GLOBAL_QUOTE",
                "symbol": ticker,
                "apikey": settings.ALPHA_VANTAGE_API_KEY,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("Global Quote", {})
        if not data or "05. price" not in data:
            return None

        sector = next(
            (s for s, ts in SECTOR_TICKERS.items() if ticker in ts), "Unknown"
        )
        return StockQuote(
            ticker=ticker,
            name=ticker,
            price=float(data["05. price"]),
            change_pct_1d=float(data.get("10. change percent", "0").rstrip("%")),
            sector=sector,
            volume=float(data.get("06. volume", 0)),
            currency="USD",
        )
    except Exception as exc:
        logger.error("Error fetching US quote %s: %s", ticker, exc)
        return None


async def fetch_us_stocks(tickers: Optional[List[str]] = None) -> Dict[str, List[dict]]:
    """Return US stock quotes grouped by sector. Results are cached for 15 min."""
    cached = await cache_get(CACHE_KEY)
    if cached:
        logger.debug("US stocks cache hit")
        return cached

    if not settings.ALPHA_VANTAGE_API_KEY:
        logger.warning("ALPHA_VANTAGE_API_KEY not set — returning mock US stock data")
        data = _mock_us_stocks()
        await cache_set(CACHE_KEY, data)
        return data

    target = tickers or ALL_TICKERS
    quotes: List[StockQuote] = []

    async with httpx.AsyncClient() as client:
        for ticker in target:
            quote = await _fetch_quote(ticker, client)
            if quote:
                quotes.append(quote)

    by_sector: Dict[str, List[dict]] = {}
    for q in quotes:
        by_sector.setdefault(q.sector or "Unknown", []).append(q.model_dump())

    result = by_sector or _mock_us_stocks()
    await cache_set(CACHE_KEY, result)
    return result


def _mock_us_stocks() -> Dict[str, List[dict]]:
    return {
        "Technology": [
            {"ticker": "AAPL", "name": "Apple Inc.", "price": 185.50,
             "change_pct_1d": 0.5, "change_pct_7d": 2.1, "sector": "Technology", "currency": "USD"},
            {"ticker": "MSFT", "name": "Microsoft Corp.", "price": 415.20,
             "change_pct_1d": 0.3, "change_pct_7d": 1.8, "sector": "Technology", "currency": "USD"},
            {"ticker": "NVDA", "name": "NVIDIA Corp.", "price": 875.00,
             "change_pct_1d": 1.2, "change_pct_7d": 5.4, "sector": "Technology", "currency": "USD"},
            {"ticker": "GOOGL", "name": "Alphabet Inc.", "price": 175.30,
             "change_pct_1d": 0.4, "change_pct_7d": 1.5, "sector": "Technology", "currency": "USD"},
        ],
        "Finance": [
            {"ticker": "JPM", "name": "JPMorgan Chase", "price": 198.40,
             "change_pct_1d": -0.2, "change_pct_7d": 0.9, "sector": "Finance", "currency": "USD"},
            {"ticker": "BAC", "name": "Bank of America", "price": 38.20,
             "change_pct_1d": -0.1, "change_pct_7d": 0.5, "sector": "Finance", "currency": "USD"},
        ],
        "Healthcare": [
            {"ticker": "JNJ", "name": "Johnson & Johnson", "price": 158.80,
             "change_pct_1d": 0.1, "change_pct_7d": -0.5, "sector": "Healthcare", "currency": "USD"},
            {"ticker": "UNH", "name": "UnitedHealth Group", "price": 490.00,
             "change_pct_1d": 0.6, "change_pct_7d": 2.3, "sector": "Healthcare", "currency": "USD"},
        ],
        "Consumer": [
            {"ticker": "AMZN", "name": "Amazon.com Inc.", "price": 185.00,
             "change_pct_1d": 0.8, "change_pct_7d": 3.2, "sector": "Consumer", "currency": "USD"},
            {"ticker": "TSLA", "name": "Tesla Inc.", "price": 245.00,
             "change_pct_1d": 1.5, "change_pct_7d": 4.1, "sector": "Consumer", "currency": "USD"},
        ],
        "Energy": [
            {"ticker": "XOM", "name": "Exxon Mobil Corp.", "price": 112.50,
             "change_pct_1d": -0.3, "change_pct_7d": -1.0, "sector": "Energy", "currency": "USD"},
        ],
    }
