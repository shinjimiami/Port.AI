"""US stock data — TradingView (primary) → Alpha Vantage → mock fallback."""
import logging
from typing import Dict, List, Optional

import httpx

from app.config import settings
from app.schemas.market import StockQuote
from app.services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

CACHE_KEY = "portai:market:us_stocks"
_AV_BASE   = "https://www.alphavantage.co/query"

SECTOR_TICKERS: Dict[str, List[str]] = {
    "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
    "Healthcare":  ["JNJ", "UNH", "PFE", "ABBV", "MRK"],
    "Finance":     ["JPM", "BAC", "WFC", "GS", "MS"],
    "Consumer":    ["AMZN", "TSLA", "NKE", "MCD", "SBUX"],
    "Energy":      ["XOM", "CVX", "SLB", "COP", "EOG"],
    "Industrial":  ["CAT", "HON", "GE", "MMM", "UPS"],
}

ALL_TICKERS = [t for tickers in SECTOR_TICKERS.values() for t in tickers]

TICKER_NAME: Dict[str, str] = {
    "AAPL": "Apple Inc.", "MSFT": "Microsoft Corp.", "NVDA": "NVIDIA Corp.",
    "GOOGL": "Alphabet Inc.", "META": "Meta Platforms",
    "JNJ": "Johnson & Johnson", "UNH": "UnitedHealth Group",
    "PFE": "Pfizer Inc.", "ABBV": "AbbVie Inc.", "MRK": "Merck & Co.",
    "JPM": "JPMorgan Chase", "BAC": "Bank of America",
    "WFC": "Wells Fargo", "GS": "Goldman Sachs", "MS": "Morgan Stanley",
    "AMZN": "Amazon.com Inc.", "TSLA": "Tesla Inc.",
    "NKE": "Nike Inc.", "MCD": "McDonald's Corp.", "SBUX": "Starbucks Corp.",
    "XOM": "Exxon Mobil Corp.", "CVX": "Chevron Corp.",
    "SLB": "SLB (Schlumberger)", "COP": "ConocoPhillips", "EOG": "EOG Resources",
    "CAT": "Caterpillar Inc.", "HON": "Honeywell Intl.",
    "GE": "GE Aerospace", "MMM": "3M Co.", "UPS": "United Parcel Service",
}


async def fetch_us_stocks(tickers: Optional[List[str]] = None) -> Dict[str, List[dict]]:
    """Return US stock quotes grouped by sector. TradingView → Alpha Vantage → mock."""
    cached = await cache_get(CACHE_KEY)
    if cached:
        logger.debug("US stocks cache hit")
        return cached

    result = await _fetch_via_tradingview(tickers)
    if not result and settings.ALPHA_VANTAGE_API_KEY:
        result = await _fetch_via_alpha_vantage(tickers)
    if not result:
        result = _mock_us_stocks()

    await cache_set(CACHE_KEY, result)
    return result


async def _fetch_via_tradingview(tickers: Optional[List[str]] = None) -> Dict[str, List[dict]]:
    try:
        from app.services.market_data.tradingview import fetch_us_quotes_tv
        tv_data = await fetch_us_quotes_tv(tickers)
        if not tv_data:
            return {}

        by_sector: Dict[str, List[dict]] = {}
        target = tickers or ALL_TICKERS
        for ticker in target:
            q = tv_data.get(ticker)
            if not q or not q.get("price"):
                continue
            sector = next((s for s, ts in SECTOR_TICKERS.items() if ticker in ts), "Unknown")
            quote = StockQuote(
                ticker=ticker,
                name=q.get("name") or TICKER_NAME.get(ticker, ticker),
                price=float(q["price"]),
                change_pct_1d=float(q.get("change_pct", 0)),
                volume=float(q.get("volume", 0)),
                sector=sector,
                currency=q.get("currency") or "USD",
            )
            by_sector.setdefault(sector, []).append(quote.model_dump())

        logger.info("US data fetched via TradingView (%d tickers)", sum(len(v) for v in by_sector.values()))
        return by_sector
    except Exception as exc:
        logger.warning("TradingView US fetch failed: %s", exc)
        return {}


async def _fetch_via_alpha_vantage(tickers: Optional[List[str]] = None) -> Dict[str, List[dict]]:
    target = tickers or ALL_TICKERS
    by_sector: Dict[str, List[dict]] = {}

    async with httpx.AsyncClient() as client:
        for ticker in target:
            try:
                resp = await client.get(
                    _AV_BASE,
                    params={"function": "GLOBAL_QUOTE", "symbol": ticker,
                            "apikey": settings.ALPHA_VANTAGE_API_KEY},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json().get("Global Quote", {})
                if not data or "05. price" not in data:
                    continue
                sector = next((s for s, ts in SECTOR_TICKERS.items() if ticker in ts), "Unknown")
                quote = StockQuote(
                    ticker=ticker,
                    name=TICKER_NAME.get(ticker, ticker),
                    price=float(data["05. price"]),
                    change_pct_1d=float(data.get("10. change percent", "0").rstrip("%")),
                    sector=sector,
                    volume=float(data.get("06. volume", 0)),
                    currency="USD",
                )
                by_sector.setdefault(sector, []).append(quote.model_dump())
            except Exception as exc:
                logger.error("Alpha Vantage quote %s: %s", ticker, exc)

    logger.info("US data fetched via Alpha Vantage (%d tickers)", sum(len(v) for v in by_sector.values()))
    return by_sector


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
