"""Celery task: runs the LangGraph pipeline in the background."""
import asyncio
import logging
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.portfolio import Portfolio
from app.schemas.portfolio import GeneratePortfolioRequest
from app.services.cache import sync_publish_progress
from app.tasks import celery_app

logger = logging.getLogger(__name__)


def _get_db() -> Session:
    return SessionLocal()


@celery_app.task(bind=True, name="portfolio.generate")
def generate_portfolio_task(self, portfolio_id: int, user_input_dict: dict):
    """
    Run the full LangGraph pipeline for a portfolio record.

    Args:
        portfolio_id: DB row to update with results.
        user_input_dict: Serialised GeneratePortfolioRequest.
    """
    db = _get_db()
    try:
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            logger.error("Portfolio %s not found", portfolio_id)
            return

        # Mark as processing
        portfolio.status = "processing"
        db.commit()
        sync_publish_progress(portfolio_id, "started", "Pipeline starting…")

        # Deserialise input
        user_input = GeneratePortfolioRequest(**user_input_dict)

        # Run async pipeline in a new event loop (Celery workers are sync)
        result = asyncio.run(_run_pipeline_with_progress(user_input, portfolio_id))

        portfolio.allocation_plan = result["allocation_plan"]
        portfolio.selected_assets = result["selected_assets"]
        portfolio.report = result["report"]
        portfolio.status = "completed"
        portfolio.completed_at = datetime.now(timezone.utc)
        db.commit()

        sync_publish_progress(portfolio_id, "completed", "Report ready")
        logger.info("Portfolio %s completed", portfolio_id)

    except Exception as exc:
        logger.error("Portfolio %s failed: %s", portfolio_id, exc, exc_info=True)
        try:
            portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if portfolio:
                portfolio.status = "failed"
                portfolio.error_message = str(exc)
                db.commit()
            sync_publish_progress(portfolio_id, "failed", str(exc))
        except Exception:
            pass
        raise self.retry(exc=exc)

    finally:
        db.close()


async def _run_pipeline_with_progress(
    user_input: GeneratePortfolioRequest,
    portfolio_id: int,
) -> dict:
    """
    Wrap the compiled graph with per-node progress events.
    Uses LangGraph's astream_events to emit each node name as it completes.
    """
    from app.agents.graph import _compiled_graph
    from app.services.cache import publish_progress

    NODE_LABELS = {
        "input_validator":          "Validating input…",
        "market_data_fetcher":      "Fetching market data…",
        "allocation_planner":       "Planning asset allocation…",
        "asset_selector":           "Selecting assets…",
        "diversification_checker":  "Checking diversification…",
        "report_generator":         "Generating report…",
    }

    initial_state = {
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

    final_state = None

    async for event in _compiled_graph.astream_events(initial_state, version="v2"):
        kind = event.get("event")
        name = event.get("name", "")

        if kind == "on_chain_start" and name in NODE_LABELS:
            await publish_progress(portfolio_id, name, NODE_LABELS[name])

        # Capture final state from the last chunk
        if kind == "on_chain_end" and name == "LangGraph":
            final_state = event.get("data", {}).get("output")

    if not final_state or not final_state.get("report"):
        # Fallback: invoke directly
        from app.agents.graph import run_pipeline
        return await run_pipeline(user_input, portfolio_id)

    return {
        "allocation_plan": final_state["allocation_plan"],
        "selected_assets": final_state["selected_assets"],
        "report": final_state["report"],
    }
