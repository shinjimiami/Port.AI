"""Node 2 — MARKET_DATA_FETCHER: aggregates live data for requested asset classes.

All three sources (IDX, US_STOCKS, CRYPTO) are now awaited concurrently.
TradingView provides real-time prices for IDX and US stocks; crypto and
fallbacks stay on their existing sources.
"""
import asyncio
import logging

from app.agents.state import PortfolioState
from app.services.market_data.crypto import fetch_crypto
from app.services.market_data.idx_stocks import fetch_idx_stocks
from app.services.market_data.us_stocks import fetch_us_stocks

logger = logging.getLogger(__name__)


async def market_data_fetcher_node(state: PortfolioState) -> PortfolioState:
    """Fetch market data only for the asset classes requested by the user."""
    asset_classes = state["user_input"].asset_classes
    errors: list[str] = list(state.get("errors", []))
    market_data: dict = {}

    fetch_tasks: dict = {}
    if "US_STOCKS" in asset_classes:
        fetch_tasks["US_STOCKS"] = fetch_us_stocks()
    if "CRYPTO" in asset_classes:
        fetch_tasks["CRYPTO"] = fetch_crypto(top_n=50)
    if "IDX" in asset_classes:
        fetch_tasks["IDX"] = fetch_idx_stocks()

    if fetch_tasks:
        keys = list(fetch_tasks.keys())
        results = await asyncio.gather(*[fetch_tasks[k] for k in keys], return_exceptions=True)
        for key, result in zip(keys, results):
            if isinstance(result, Exception):
                logger.error("Failed to fetch %s: %s", key, result)
                errors.append(f"Could not fetch {key} data: {result}")
                market_data[key] = {}
            else:
                market_data[key] = result

    logger.info("MarketDataFetcher: fetched data for %s", list(market_data.keys()))
    return {**state, "market_data": market_data, "errors": errors}
