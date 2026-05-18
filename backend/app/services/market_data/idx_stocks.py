"""IDX stock data — TradingView (primary) with yfinance fallback.

fetch_idx_stocks() is now async to support the TradingView WebSocket bridge.
The market_data_fetcher agent awaits it alongside the other async fetches.
"""
import logging
from typing import Dict, List, Optional

from app.schemas.market import StockQuote
from app.services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

CACHE_KEY = "portai:market:idx_stocks"

IDX_TICKERS: Dict[str, List[str]] = {
    "Finance":    ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK"],
    "Telecom":    ["TLKM.JK", "EXCL.JK", "ISAT.JK"],
    "Consumer":   ["ICBP.JK", "INDF.JK", "UNVR.JK", "MYOR.JK"],
    "Technology": ["GOTO.JK", "BUKA.JK", "EMTK.JK"],
    "Energy":     ["PGAS.JK", "MEDC.JK", "ADRO.JK"],
    "Industrial": ["ASII.JK", "UNTR.JK", "SMGR.JK"],
    "Property":   ["BSDE.JK", "CTRA.JK", "PWON.JK"],
}

ALL_IDX_TICKERS = [t for ts in IDX_TICKERS.values() for t in ts]

TICKER_NAME: Dict[str, str] = {
    "BBCA.JK": "Bank Central Asia",    "BBRI.JK": "Bank Rakyat Indonesia",
    "BMRI.JK": "Bank Mandiri",         "BBNI.JK": "Bank Negara Indonesia",
    "TLKM.JK": "Telkom Indonesia",     "EXCL.JK": "XL Axiata",
    "ISAT.JK": "Indosat Ooredoo",      "ICBP.JK": "Indofood CBP",
    "INDF.JK": "Indofood",             "UNVR.JK": "Unilever Indonesia",
    "MYOR.JK": "Mayora Indah",         "GOTO.JK": "GoTo Gojek Tokopedia",
    "BUKA.JK": "Bukalapak",            "EMTK.JK": "Elang Mahkota Teknologi",
    "PGAS.JK": "Perusahaan Gas Negara","MEDC.JK": "Medco Energi",
    "ADRO.JK": "Adaro Energy",         "ASII.JK": "Astra International",
    "UNTR.JK": "United Tractors",      "SMGR.JK": "Semen Indonesia",
    "BSDE.JK": "BSD City",             "CTRA.JK": "Ciputra Development",
    "PWON.JK": "Pakuwon Jati",
}


async def fetch_idx_stocks(tickers: Optional[List[str]] = None) -> Dict[str, List[dict]]:
    """Return IDX stock quotes grouped by sector. TradingView → yfinance → mock."""
    cached = await cache_get(CACHE_KEY)
    if cached:
        logger.debug("IDX stocks cache hit")
        return cached

    result = await _fetch_via_tradingview(tickers)
    if not result:
        result = await _fetch_via_yfinance(tickers)
    if not result:
        result = _mock_idx_stocks()

    await cache_set(CACHE_KEY, result)
    return result


async def _fetch_via_tradingview(tickers: Optional[List[str]] = None) -> Dict[str, List[dict]]:
    try:
        from app.services.market_data.tradingview import fetch_idx_quotes_tv
        tv_data = await fetch_idx_quotes_tv()
        if not tv_data:
            return {}

        by_sector: Dict[str, List[dict]] = {}
        target = tickers or ALL_IDX_TICKERS
        for ticker in target:
            q = tv_data.get(ticker)
            if not q or not q.get("price"):
                continue
            sector = next((s for s, ts in IDX_TICKERS.items() if ticker in ts), "Unknown")
            quote = StockQuote(
                ticker=ticker,
                name=q.get("name") or TICKER_NAME.get(ticker, ticker.replace(".JK", "")),
                price=float(q["price"]),
                change_pct_1d=float(q.get("change_pct", 0)),
                volume=float(q.get("volume", 0)),
                sector=sector,
                currency=q.get("currency") or "IDR",
            )
            by_sector.setdefault(sector, []).append(quote.model_dump())

        logger.info("IDX data fetched via TradingView (%d tickers)", sum(len(v) for v in by_sector.values()))
        return by_sector
    except Exception as exc:
        logger.warning("TradingView IDX fetch failed: %s", exc)
        return {}


async def _fetch_via_yfinance(tickers: Optional[List[str]] = None) -> Dict[str, List[dict]]:
    try:
        import yfinance as yf
    except ImportError:
        return {}

    target = tickers or ALL_IDX_TICKERS
    by_sector: Dict[str, List[dict]] = {}
    for ticker in target:
        try:
            info = yf.Ticker(ticker).fast_info
            sector = next((s for s, ts in IDX_TICKERS.items() if ticker in ts), "Unknown")
            price = float(getattr(info, "last_price", 0) or 0)
            if price == 0:
                continue
            quote = StockQuote(
                ticker=ticker,
                name=TICKER_NAME.get(ticker, ticker.replace(".JK", "")),
                price=price,
                sector=sector,
                currency="IDR",
            )
            by_sector.setdefault(sector, []).append(quote.model_dump())
        except Exception as exc:
            logger.warning("Skipping IDX ticker %s: %s", ticker, exc)

    logger.info("IDX data fetched via yfinance (%d tickers)", sum(len(v) for v in by_sector.values()))
    return by_sector


def _mock_idx_stocks() -> Dict[str, List[dict]]:
    return {
        "Finance": [
            {"ticker": "BBCA.JK", "name": "Bank Central Asia", "price": 9875.0,
             "change_pct_1d": 0.3, "change_pct_7d": 1.5, "sector": "Finance", "currency": "IDR"},
            {"ticker": "BBRI.JK", "name": "Bank Rakyat Indonesia", "price": 5200.0,
             "change_pct_1d": -0.2, "change_pct_7d": 0.8, "sector": "Finance", "currency": "IDR"},
            {"ticker": "BMRI.JK", "name": "Bank Mandiri", "price": 6350.0,
             "change_pct_1d": 0.5, "change_pct_7d": 2.1, "sector": "Finance", "currency": "IDR"},
        ],
        "Telecom": [
            {"ticker": "TLKM.JK", "name": "Telkom Indonesia", "price": 3890.0,
             "change_pct_1d": 0.1, "change_pct_7d": -0.3, "sector": "Telecom", "currency": "IDR"},
            {"ticker": "EXCL.JK", "name": "XL Axiata", "price": 2540.0,
             "change_pct_1d": -0.1, "change_pct_7d": -0.7, "sector": "Telecom", "currency": "IDR"},
        ],
        "Technology": [
            {"ticker": "GOTO.JK", "name": "GoTo Gojek Tokopedia", "price": 58.0,
             "change_pct_1d": 1.8, "change_pct_7d": 5.2, "sector": "Technology", "currency": "IDR"},
            {"ticker": "BUKA.JK", "name": "Bukalapak", "price": 142.0,
             "change_pct_1d": 0.7, "change_pct_7d": 2.8, "sector": "Technology", "currency": "IDR"},
        ],
        "Consumer": [
            {"ticker": "ICBP.JK", "name": "Indofood CBP", "price": 10850.0,
             "change_pct_1d": 0.0, "change_pct_7d": 0.5, "sector": "Consumer", "currency": "IDR"},
            {"ticker": "UNVR.JK", "name": "Unilever Indonesia", "price": 2840.0,
             "change_pct_1d": -0.2, "change_pct_7d": -0.9, "sector": "Consumer", "currency": "IDR"},
        ],
        "Energy": [
            {"ticker": "ADRO.JK", "name": "Adaro Energy", "price": 2840.0,
             "change_pct_1d": -0.4, "change_pct_7d": -1.2, "sector": "Energy", "currency": "IDR"},
        ],
        "Industrial": [
            {"ticker": "ASII.JK", "name": "Astra International", "price": 5400.0,
             "change_pct_1d": 0.2, "change_pct_7d": 0.7, "sector": "Industrial", "currency": "IDR"},
        ],
    }
