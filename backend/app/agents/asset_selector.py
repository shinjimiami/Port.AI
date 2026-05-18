"""Node 4 — ASSET_SELECTOR: LLM picks specific assets within each allocated class."""
import json
import logging
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm import build_llm
from app.agents.state import PortfolioState

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a professional stock and crypto analyst.
Select specific assets from the provided market data to build a diversified portfolio.

Rules:
- Choose 3-6 assets per asset class (fewer if budget is small).
- Diversify across sectors within each class.
- Prefer assets with positive 7d/30d momentum but avoid chasing recent spikes.
- No single asset should exceed 25% of total portfolio value.
- No single sector should exceed 40% of a given asset class allocation.
- For each selected asset provide: ticker, name, asset_class, sector,
  allocation_percentage (of total portfolio), amount (in budget currency),
  reasoning (2-3 sentences), current_price, expected_return.

If diversification_feedback is provided, address it specifically.

Return ONLY a JSON array of asset objects, no markdown fences."""


def _flatten_market_data(market_data: Dict[str, Any], asset_class: str) -> List[dict]:
    """Flatten sector-grouped market data into a flat list for the prompt."""
    class_data = market_data.get(asset_class, {})
    flat = []
    for sector, items in class_data.items():
        for item in items:
            item["sector"] = item.get("sector") or sector
            flat.append(item)
    return flat[:20]  # cap to avoid context overflow


async def asset_selector_node(state: PortfolioState) -> PortfolioState:
    allocation_plan = state["allocation_plan"]
    market_data = state["market_data"]
    feedback = state.get("diversification_feedback")
    budget = float(state["user_input"].budget)
    errors: list[str] = list(state.get("errors", []))

    prompt_parts = [
        f"Total budget: {budget} {state['user_input'].currency}",
        f"Risk profile: {state.get('inferred_risk', 'moderate')}",
        f"Investment horizon: {state['user_input'].horizon}",
    ]
    if feedback:
        prompt_parts.append(f"\nDiversification feedback to address: {feedback}")

    prompt_parts.append("\nAllocation plan:")
    for ac, info in allocation_plan.items():
        prompt_parts.append(f"  {ac}: {info['percentage']}% = {info['amount']} {state['user_input'].currency}")
        candidates = _flatten_market_data(market_data, ac)
        if candidates:
            # Keep only essential fields to reduce token usage
            slim = [
                {k: c.get(k) for k in ("ticker", "symbol", "name", "sector", "price", "price_usd", "change_pct_1d", "change_pct_7d")}
                for c in candidates[:6]
            ]
            prompt_parts.append(f"  Available {ac} candidates: {json.dumps(slim, default=str)}")

    prompt = "\n".join(prompt_parts)

    try:
        llm = build_llm(max_tokens=4096)
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        selected_assets: List[dict] = json.loads(raw)
        logger.info("AssetSelector: selected %d assets", len(selected_assets))
    except Exception as exc:
        logger.error("AssetSelector LLM call failed: %s — using fallback", exc)
        errors.append(f"Asset selector used fallback due to: {exc}")
        selected_assets = _fallback_assets(allocation_plan, market_data, budget)

    return {**state, "selected_assets": selected_assets, "errors": errors}


def _fallback_assets(
    allocation_plan: Dict[str, Any],
    market_data: Dict[str, Any],
    budget: float,
) -> List[dict]:
    """Pick the first available candidate per asset class as a minimal fallback."""
    assets = []
    for ac, info in allocation_plan.items():
        flat = _flatten_market_data(market_data, ac)
        if not flat:
            continue
        top = flat[0]
        pct = info["percentage"]
        amount = info["amount"]
        # Split across 2 assets if available
        for i, candidate in enumerate(flat[:2]):
            share = pct / 2
            assets.append({
                "ticker": candidate.get("ticker") or candidate.get("symbol", "???"),
                "name": candidate.get("name", "Unknown"),
                "asset_class": ac,
                "sector": candidate.get("sector", "Unknown"),
                "allocation_percentage": share,
                "amount": round(amount / 2, 2),
                "reasoning": "Selected as top available asset in this class.",
                "current_price": candidate.get("price") or candidate.get("price_usd"),
                "expected_return": "N/A",
            })
    return assets
