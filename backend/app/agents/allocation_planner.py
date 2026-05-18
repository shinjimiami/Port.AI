"""Node 3 — ALLOCATION_PLANNER: LLM decides % split between asset classes."""
import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm import build_llm
from app.agents.state import PortfolioState

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a professional portfolio allocation specialist following Modern Portfolio Theory.
Your job is to decide what percentage of the investment budget to allocate to each asset class.

Rules:
- Percentages must sum to exactly 100.
- Conservative profile: bonds/stable assets preferred; crypto ≤ 10%.
- Moderate profile: balanced mix; crypto ≤ 30%.
- Aggressive profile: more equity/crypto; crypto ≤ 50%.
- Short horizon (≤3 months): weight toward stability.
- Long horizon (≥3 years): more growth assets acceptable.
- Only include asset classes the user selected.

Return ONLY valid JSON, no markdown fences, in this exact format:
{
  "reasoning": "<2-3 sentence explanation>",
  "allocation": {
    "US_STOCKS": {"percentage": <int>, "rationale": "<string>"},
    "IDX":       {"percentage": <int>, "rationale": "<string>"},
    "CRYPTO":    {"percentage": <int>, "rationale": "<string>"}
  }
}
Only include keys for asset classes requested. Omit the rest."""


async def allocation_planner_node(state: PortfolioState) -> PortfolioState:
    user_input = state["user_input"]
    risk = state.get("inferred_risk") or user_input.risk_tolerance or "moderate"
    errors: list[str] = list(state.get("errors", []))

    prompt = f"""
Budget: {user_input.budget} {user_input.currency}
Investment horizon: {user_input.horizon}
Risk profile: {risk}
Requested asset classes: {user_input.asset_classes}

Allocate the portfolio across these asset classes.
"""

    try:
        llm = build_llm(max_tokens=1024)
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        raw = response.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        allocation = parsed.get("allocation", {})
        logger.info("AllocationPlanner result: %s", allocation)
    except Exception as exc:
        logger.error("AllocationPlanner LLM call failed: %s — using fallback", exc)
        errors.append(f"Allocation planner used fallback due to: {exc}")
        allocation = _fallback_allocation(user_input.asset_classes, risk)

    # Attach dollar amounts
    budget = float(user_input.budget)
    plan: dict = {}
    for asset_class, info in allocation.items():
        if asset_class in user_input.asset_classes:
            pct = float(info.get("percentage", 0))
            plan[asset_class] = {
                "percentage": pct,
                "amount": round(budget * pct / 100, 2),
                "rationale": info.get("rationale", ""),
            }

    return {**state, "allocation_plan": plan, "errors": errors}


def _fallback_allocation(asset_classes: list[str], risk: str) -> dict:
    """Rule-based fallback when the LLM call fails."""
    presets = {
        "conservative": {"US_STOCKS": 60, "IDX": 30, "CRYPTO": 10},
        "moderate":     {"US_STOCKS": 40, "IDX": 35, "CRYPTO": 25},
        "aggressive":   {"US_STOCKS": 30, "IDX": 25, "CRYPTO": 45},
    }
    base = presets.get(risk, presets["moderate"])
    # Keep only requested classes and normalise to 100
    filtered = {k: v for k, v in base.items() if k in asset_classes}
    total = sum(filtered.values()) or 1
    return {
        k: {"percentage": round(v / total * 100), "rationale": "Fallback rule-based allocation"}
        for k, v in filtered.items()
    }
