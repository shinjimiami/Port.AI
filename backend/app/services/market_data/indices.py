"""Live market indices via yfinance."""
import asyncio
import logging
from typing import Any, Dict, List

from app.services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)
CACHE_KEY = "portai:market:indices"
CACHE_TTL = 300  # 5 min

INDICES_META = [
    {"symbol": "^GSPC",   "name": "S&P 500",       "currency": "USD"},
    {"symbol": "^IXIC",   "name": "NASDAQ",         "currency": "USD"},
    {"symbol": "^DJI",    "name": "Dow Jones",      "currency": "USD"},
    {"symbol": "^JKSE",   "name": "IDX Composite",  "currency": "IDR"},
    {"symbol": "BTC-USD", "name": "Bitcoin",        "currency": "USD"},
    {"symbol": "ETH-USD", "name": "Ethereum",       "currency": "USD"},
    {"symbol": "GC=F",    "name": "Gold",           "currency": "USD"},
]


async def fetch_indices() -> List[Dict[str, Any]]:
    """Fetch live index/price data via yfinance. Cached 5 min."""
    cached = await cache_get(CACHE_KEY)
    if cached:
        return cached

    result = await asyncio.to_thread(_fetch_indices_sync)
    await cache_set(CACHE_KEY, result, ttl=CACHE_TTL)
    return result


def _fetch_indices_sync() -> List[Dict[str, Any]]:
    try:
        import yfinance as yf
        symbols = [m["symbol"] for m in INDICES_META]
        tickers = yf.Tickers(" ".join(symbols))
        result = []
        for meta in INDICES_META:
            sym = meta["symbol"]
            try:
                t = tickers.tickers[sym]
                hist = t.history(period="5d")
                if hist.empty:
                    raise ValueError("no data")
                close_today = float(hist["Close"].iloc[-1])
                close_prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else close_today
                change = close_today - close_prev
                change_pct = (change / close_prev * 100) if close_prev else 0.0
                result.append({
                    "symbol": sym,
                    "name": meta["name"],
                    "price": round(close_today, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "currency": meta["currency"],
                })
            except Exception as exc:
                logger.warning("yfinance failed for %s: %s", sym, exc)
        if result:
            return result
    except Exception as exc:
        logger.error("Indices fetch failed entirely: %s", exc)
    return _mock_indices()


def _mock_indices() -> List[Dict[str, Any]]:
    return [
        {"symbol": "^GSPC",   "name": "S&P 500",       "price": 5204.34,  "change": 23.15,   "change_pct": 0.45,  "currency": "USD"},
        {"symbol": "^IXIC",   "name": "NASDAQ",         "price": 16340.87, "change": 88.02,   "change_pct": 0.54,  "currency": "USD"},
        {"symbol": "^DJI",    "name": "Dow Jones",      "price": 38589.16, "change": 56.76,   "change_pct": 0.15,  "currency": "USD"},
        {"symbol": "^JKSE",   "name": "IDX Composite",  "price": 7312.50,  "change": 54.30,   "change_pct": 0.75,  "currency": "IDR"},
        {"symbol": "BTC-USD", "name": "Bitcoin",        "price": 67820.50, "change": 1245.00, "change_pct": 1.87,  "currency": "USD"},
        {"symbol": "ETH-USD", "name": "Ethereum",       "price": 3562.10,  "change": 42.30,   "change_pct": 1.20,  "currency": "USD"},
        {"symbol": "GC=F",    "name": "Gold",           "price": 2341.80,  "change": 8.50,    "change_pct": 0.36,  "currency": "USD"},
    ]
