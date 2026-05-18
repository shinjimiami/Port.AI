"""
Fundamental Analysis LangGraph pipeline.

Flow:
  START
  → file_extractor        (PDF/Excel → structured financial data)
  → ratio_calculator      (pure Python ratios)
  → trend_analyzer        (YoY growth + pattern detection)
  → red_flag_detector     (anomaly scanning)
  → valuation_engine      (DCF + relative valuation)
  → entry_signal_scorer   (100-pt scoring)
  → narrative_generator   (Groq → full Bahasa Indonesia report)
  → END
"""
import logging
from typing import Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph

from app.agents.fundamental.entry_signal_scorer import entry_signal_scorer_node
from app.agents.fundamental.file_extractor import file_extractor_node
from app.agents.fundamental.narrative_generator import narrative_generator_node
from app.agents.fundamental.ratio_calculator import ratio_calculator_node
from app.agents.fundamental.red_flag_detector import red_flag_detector_node
from app.agents.fundamental.state import FileInput, FundamentalState
from app.agents.fundamental.trend_analyzer import trend_analyzer_node
from app.agents.fundamental.valuation_engine import valuation_engine_node

logger = logging.getLogger(__name__)


def _build_graph() -> StateGraph:
    g = StateGraph(FundamentalState)

    g.add_node("file_extractor",       file_extractor_node)
    g.add_node("ratio_calculator",     ratio_calculator_node)
    g.add_node("trend_analyzer",       trend_analyzer_node)
    g.add_node("red_flag_detector",    red_flag_detector_node)
    g.add_node("valuation_engine",     valuation_engine_node)
    g.add_node("entry_signal_scorer",  entry_signal_scorer_node)
    g.add_node("narrative_generator",  narrative_generator_node)

    g.add_edge(START,                  "file_extractor")
    g.add_edge("file_extractor",       "ratio_calculator")
    g.add_edge("ratio_calculator",     "trend_analyzer")
    g.add_edge("trend_analyzer",       "red_flag_detector")
    g.add_edge("red_flag_detector",    "valuation_engine")
    g.add_edge("valuation_engine",     "entry_signal_scorer")
    g.add_edge("entry_signal_scorer",  "narrative_generator")
    g.add_edge("narrative_generator",  END)

    return g


_compiled = _build_graph().compile()


async def run_fundamental_pipeline(
    ticker: str,
    files: List[FileInput],
    current_price: Optional[float] = None,
) -> Dict[str, Any]:
    """Entry point for the fundamental analysis pipeline."""
    initial: FundamentalState = {
        "ticker":          ticker.upper(),
        "current_price":   current_price,
        "files":           files,
        "extracted_data":  {},
        "normalized_data": [],
        "ratios":          {},
        "trend_analysis":  {},
        "red_flags":       [],
        "valuation":       {},
        "entry_signal":    {},
        "narrative_report": "",
        "errors":          [],
    }

    logger.info("Fundamental pipeline starting for %s (%d file(s))", ticker, len(files))
    final = await _compiled.ainvoke(initial)
    logger.info("Fundamental pipeline completed for %s — errors: %s",
                ticker, final.get("errors"))
    return final
