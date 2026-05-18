"""IDX stock data via yfinance — with Redis cache (sync)."""
import logging
from typing import Dict, List, Optional

from app.schemas.market import StockQuote
from app.services.cache import sync_cache_get, sync_cache_set

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


def fetch_idx_stocks(tickers: Optional[List[str]] = None) -> Dict[str, List[dict]]:
    """Return IDX stock quotes grouped by sector. Results are cached for 15 min."""
    cached = sync_cache_get(CACHE_KEY)
    if cached:
        logger.debug("IDX stocks cache hit")
        return cached

    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance not installed — returning mock IDX data")
        data = _mock_idx_stocks()
        sync_cache_set(CACHE_KEY, data)
        return data

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
                name=ticker.replace(".JK", ""),
                price=price,
                sector=sector,
                currency="IDR",
            )
            by_sector.setdefault(sector, []).append(quote.model_dump())
        except Exception as exc:
            logger.warning("Skipping IDX ticker %s: %s", ticker, exc)

    result = by_sector if by_sector else _mock_idx_stocks()
    sync_cache_set(CACHE_KEY, result)
    return result


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
