"""Python bridge to the Node.js TradingView-API script.

Calls backend/tradingview/fetch_quotes.js via subprocess and returns
parsed quote data. Used by the AI agent as the primary real-time
data source; individual services fall back to yfinance / Alpha Vantage
if this fails.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Absolute path to the Node.js script
_TV_SCRIPT = Path(__file__).parent.parent.parent.parent / "tradingview" / "fetch_quotes.js"

# --------------------------------------------------------------------------- #
# Symbol mappings
# --------------------------------------------------------------------------- #

# IDX tickers (yfinance .JK suffix → TradingView IDX:TICKER)
IDX_TV_SYMBOLS: Dict[str, str] = {
    "BBCA.JK": "IDX:BBCA", "BBRI.JK": "IDX:BBRI", "BMRI.JK": "IDX:BMRI",
    "BBNI.JK": "IDX:BBNI", "TLKM.JK": "IDX:TLKM", "EXCL.JK":  "IDX:EXCL",
    "ISAT.JK": "IDX:ISAT", "ICBP.JK": "IDX:ICBP", "INDF.JK":  "IDX:INDF",
    "UNVR.JK": "IDX:UNVR", "MYOR.JK": "IDX:MYOR", "GOTO.JK":  "IDX:GOTO",
    "BUKA.JK": "IDX:BUKA", "EMTK.JK": "IDX:EMTK", "PGAS.JK":  "IDX:PGAS",
    "MEDC.JK": "IDX:MEDC", "ADRO.JK": "IDX:ADRO", "ASII.JK":  "IDX:ASII",
    "UNTR.JK": "IDX:UNTR", "SMGR.JK": "IDX:SMGR", "BSDE.JK":  "IDX:BSDE",
    "CTRA.JK": "IDX:CTRA", "PWON.JK": "IDX:PWON",
}

# US tickers → TradingView EXCHANGE:TICKER
US_TV_SYMBOLS: Dict[str, str] = {
    # Technology (NASDAQ)
    "AAPL": "NASDAQ:AAPL", "MSFT": "NASDAQ:MSFT", "NVDA": "NASDAQ:NVDA",
    "GOOGL": "NASDAQ:GOOGL", "META": "NASDAQ:META",
    # Consumer (mixed)
    "AMZN": "NASDAQ:AMZN", "TSLA": "NASDAQ:TSLA",
    "NKE": "NYSE:NKE",   "MCD": "NYSE:MCD",   "SBUX": "NASDAQ:SBUX",
    # Finance (NYSE)
    "JPM": "NYSE:JPM", "BAC": "NYSE:BAC", "WFC": "NYSE:WFC",
    "GS":  "NYSE:GS",  "MS":  "NYSE:MS",
    # Healthcare (NYSE)
    "JNJ": "NYSE:JNJ", "UNH": "NYSE:UNH", "PFE": "NYSE:PFE",
    "ABBV": "NYSE:ABBV", "MRK": "NYSE:MRK",
    # Energy (NYSE)
    "XOM": "NYSE:XOM", "CVX": "NYSE:CVX", "SLB": "NYSE:SLB",
    "COP": "NYSE:COP", "EOG": "NYSE:EOG",
    # Industrial (NYSE)
    "CAT": "NYSE:CAT", "HON": "NASDAQ:HON", "GE": "NYSE:GE",
    "MMM": "NYSE:MMM", "UPS": "NYSE:UPS",
}

# Reverse maps: TV symbol → original ticker
_IDX_REVERSE  = {v: k for k, v in IDX_TV_SYMBOLS.items()}
_US_REVERSE   = {v: k for k, v in US_TV_SYMBOLS.items()}


# --------------------------------------------------------------------------- #
# Core bridge
# --------------------------------------------------------------------------- #

async def fetch_tradingview_quotes(
    tv_symbols: List[str],
    timeout: int = 28,
) -> Dict[str, dict]:
    """Run the Node.js script and return a dict keyed by TV symbol."""
    if not tv_symbols:
        return {}

    if not _TV_SCRIPT.exists():
        logger.error("TradingView script not found at %s", _TV_SCRIPT)
        return {}

    from app.config import settings
    node_bin = settings.NODE_BIN

    try:
        proc = await asyncio.create_subprocess_exec(
            node_bin, str(_TV_SCRIPT), *tv_symbols,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(_TV_SCRIPT.parent),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        if stderr:
            logger.debug("TV script stderr: %s", stderr.decode(errors="replace").strip())

        raw = stdout.decode(errors="replace").strip()
        if not raw:
            return {}

        return json.loads(raw)

    except asyncio.TimeoutError:
        logger.error("TradingView script timed out after %ds", timeout)
        try:
            proc.kill()
        except Exception:
            pass
        return {}
    except Exception as exc:
        logger.error("TradingView script error: %s", exc)
        return {}


# --------------------------------------------------------------------------- #
# High-level helpers (called by market data services)
# --------------------------------------------------------------------------- #

async def fetch_idx_quotes_tv() -> Optional[Dict[str, dict]]:
    """Return raw TV quotes for all IDX tickers, keyed by JK ticker."""
    tv_syms = list(IDX_TV_SYMBOLS.values())
    raw = await fetch_tradingview_quotes(tv_syms)
    if not raw:
        return None

    out: Dict[str, dict] = {}
    for tv_sym, quote in raw.items():
        if "error" in quote:
            logger.warning("TV error for %s: %s", tv_sym, quote["error"])
            continue
        jk = _IDX_REVERSE.get(tv_sym, tv_sym)
        out[jk] = quote
    return out or None


async def fetch_us_quotes_tv(tickers: Optional[List[str]] = None) -> Optional[Dict[str, dict]]:
    """Return raw TV quotes for US tickers, keyed by plain ticker."""
    target = tickers or list(US_TV_SYMBOLS.keys())
    tv_syms = [US_TV_SYMBOLS[t] for t in target if t in US_TV_SYMBOLS]
    raw = await fetch_tradingview_quotes(tv_syms)
    if not raw:
        return None

    out: Dict[str, dict] = {}
    for tv_sym, quote in raw.items():
        if "error" in quote:
            logger.warning("TV error for %s: %s", tv_sym, quote["error"])
            continue
        ticker = _US_REVERSE.get(tv_sym, tv_sym)
        out[ticker] = quote
    return out or None
