"""Node 2 — MARKET_DATA_FETCHER: aggregates live data for requested asset classes."""
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

    fetch_tasks = {}
    if "US_STOCKS" in asset_classes:
        fetch_tasks["US_STOCKS"] = fetch_us_stocks()
    if "CRYPTO" in asset_classes:
        fetch_tasks["CRYPTO"] = fetch_crypto(top_n=50)

    # Run async fetches in parallel
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

    # IDX is synchronous (yfinance)
    if "IDX" in asset_classes:
        try:
            market_data["IDX"] = fetch_idx_stocks()
        except Exception as exc:
            logger.error("Failed to fetch IDX: %s", exc)
            errors.append(f"Could not fetch IDX data: {exc}")
            market_data["IDX"] = {}

    logger.info("MarketDataFetcher: fetched data for %s", list(market_data.keys()))
    return {**state, "market_data": market_data, "errors": errors}
