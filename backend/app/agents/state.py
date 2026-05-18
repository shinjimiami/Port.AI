"""Shared state schema for the PortAI LangGraph pipeline."""
from typing import Any, Dict, List, Optional, TypedDict

from app.schemas.portfolio import GeneratePortfolioRequest


class PortfolioState(TypedDict):
    # Input
    user_input: GeneratePortfolioRequest

    # Enriched by INPUT_VALIDATOR
    inferred_risk: Optional[str]            # "conservative"|"moderate"|"aggressive"

    # Enriched by MARKET_DATA_FETCHER
    market_data: Dict[str, Any]             # {asset_class: {sector: [quotes]}}

    # Enriched by ALLOCATION_PLANNER
    allocation_plan: Dict[str, Any]         # {asset_class: {percentage, amount}}

    # Enriched by ASSET_SELECTOR
    selected_assets: List[Dict[str, Any]]

    # Enriched by DIVERSIFICATION_CHECKER
    diversification_ok: bool
    diversification_feedback: Optional[str]
    retry_count: int

    # Final output
    report: Optional[Dict[str, Any]]

    # Error accumulation
    errors: List[str]
