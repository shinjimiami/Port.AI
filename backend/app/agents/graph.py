"""
PortAI LangGraph pipeline.

Flow:
  START
  → input_validator
  → market_data_fetcher
  → allocation_planner
  → asset_selector
  → diversification_checker
      ↘ (fail, retry_count < MAX) → asset_selector   (loop)
      ↘ (pass)                    → report_generator
  → END
"""
import logging
from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from app.agents.allocation_planner import allocation_planner_node
from app.agents.asset_selector import asset_selector_node
from app.agents.diversification_checker import diversification_checker_node
from app.agents.input_validator import input_validator_node
from app.agents.market_data_fetcher import market_data_fetcher_node
from app.agents.report_generator import report_generator_node
from app.agents.state import PortfolioState
from app.schemas.portfolio import GeneratePortfolioRequest

logger = logging.getLogger(__name__)


# ── Conditional edge ──────────────────────────────────────────────────────────

def diversification_router(state: PortfolioState) -> str:
    """Route back to asset_selector on failure, forward to report_generator on pass."""
    if state.get("diversification_ok"):
        return "report_generator"
    return "asset_selector"


# ── Build graph ───────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(PortfolioState)

    graph.add_node("input_validator", input_validator_node)
    graph.add_node("market_data_fetcher", market_data_fetcher_node)
    graph.add_node("allocation_planner", allocation_planner_node)
    graph.add_node("asset_selector", asset_selector_node)
    graph.add_node("diversification_checker", diversification_checker_node)
    graph.add_node("report_generator", report_generator_node)

    graph.add_edge(START, "input_validator")
    graph.add_edge("input_validator", "market_data_fetcher")
    graph.add_edge("market_data_fetcher", "allocation_planner")
    graph.add_edge("allocation_planner", "asset_selector")
    graph.add_edge("asset_selector", "diversification_checker")

    # Conditional: loop back to asset_selector or proceed to report
    graph.add_conditional_edges(
        "diversification_checker",
        diversification_router,
        {
            "asset_selector": "asset_selector",
            "report_generator": "report_generator",
        },
    )

    graph.add_edge("report_generator", END)
    return graph


# Compile once at module load (reused across requests)
_compiled_graph = build_graph().compile()


# ── Public entry point ────────────────────────────────────────────────────────

async def run_pipeline(
    user_input: GeneratePortfolioRequest,
    portfolio_id: int,
) -> Dict[str, Any]:
    """
    Execute the full agent pipeline and return the relevant output fields.
    Raises on unrecoverable errors.
    """
    initial_state: PortfolioState = {
        "user_input": user_input,
        "inferred_risk": None,
        "market_data": {},
        "allocation_plan": {},
        "selected_assets": [],
        "diversification_ok": False,
        "diversification_feedback": None,
        "retry_count": 0,
        "report": None,
        "errors": [],
    }

    logger.info("Pipeline starting for portfolio_id=%s", portfolio_id)
    final_state = await _compiled_graph.ainvoke(initial_state)
    logger.info(
        "Pipeline completed for portfolio_id=%s — errors: %s",
        portfolio_id,
        final_state.get("errors"),
    )

    if not final_state.get("report"):
        raise RuntimeError("Pipeline completed but no report was generated.")

    return {
        "allocation_plan": final_state["allocation_plan"],
        "selected_assets": final_state["selected_assets"],
        "report": final_state["report"],
    }
