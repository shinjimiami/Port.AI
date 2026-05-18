"""Portfolio API: generate, history, detail, save, status, stream."""
import asyncio
import json
import logging
from datetime import date, datetime, timezone
from typing import AsyncGenerator, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import (
    GeneratePortfolioRequest,
    PortfolioListItem,
    PortfolioResponse,
)
from app.services.cache import get_progress

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_rate_limit_redis(user_id: int) -> None:
    """Redis-based rate limit — faster than a DB count query."""
    from app.services.cache import _sync_redis
    key = f"portai:ratelimit:{user_id}:{date.today().isoformat()}"
    r = _sync_redis()
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, 86_400)      # 24-hour TTL
    count, _ = pipe.execute()
    if count > settings.MAX_DAILY_GENERATIONS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Daily limit of {settings.MAX_DAILY_GENERATIONS} portfolio "
                "generations reached. Try again tomorrow."
            ),
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=PortfolioResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_portfolio(
    payload: GeneratePortfolioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger async portfolio generation.
    Returns 202 immediately; poll GET /portfolio/{id} or stream GET /portfolio/{id}/stream.
    """
    _check_rate_limit_redis(current_user.id)

    portfolio = Portfolio(
        user_id=current_user.id,
        budget=payload.budget,
        currency=payload.currency,
        horizon=payload.horizon,
        asset_classes=payload.asset_classes,
        risk_tolerance=payload.risk_tolerance,
        status="pending",
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    # Dispatch to Celery
    from app.tasks.portfolio import generate_portfolio_task
    generate_portfolio_task.delay(portfolio.id, payload.model_dump())

    logger.info(
        "Portfolio %s queued for user %s", portfolio.id, current_user.id
    )
    return portfolio


@router.get("/history", response_model=List[PortfolioListItem])
def portfolio_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Portfolio)
        .filter(Portfolio.user_id == current_user.id)
        .order_by(Portfolio.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
        .first()
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.get("/{portfolio_id}/status")
async def portfolio_status(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lightweight status check + current pipeline node for polling."""
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
        .first()
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    progress = await get_progress(portfolio_id)
    return {
        "id": portfolio.id,
        "status": portfolio.status,
        "current_node": progress.get("node") if progress else None,
        "message": progress.get("message") if progress else None,
        "created_at": portfolio.created_at,
        "completed_at": portfolio.completed_at,
    }


@router.get("/{portfolio_id}/stream")
async def portfolio_stream(
    portfolio_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Server-Sent Events stream for real-time pipeline progress.
    Subscribes to Redis Pub/Sub channel and forwards events until done/error.
    """
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
        .first()
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # If already finished, return a single event
    if portfolio.status in ("completed", "failed"):
        async def finished_stream():
            data = json.dumps({"node": portfolio.status, "message": "Pipeline already finished."})
            yield f"data: {data}\n\n"
        return StreamingResponse(finished_stream(), media_type="text/event-stream")

    return StreamingResponse(
        _sse_generator(portfolio_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _sse_generator(portfolio_id: int, request: Request) -> AsyncGenerator[str, None]:
    """Subscribe to Redis pub/sub and yield SSE events until pipeline ends."""
    import redis.asyncio as aioredis
    from app.config import settings

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    channel = f"portai:progress:{portfolio_id}"
    await pubsub.subscribe(channel)

    # Keep-alive heartbeat every 15s so the connection doesn't time out
    HEARTBEAT_INTERVAL = 15
    last_heartbeat = asyncio.get_event_loop().time()
    TERMINAL_NODES = {"completed", "failed"}

    try:
        while True:
            if await request.is_disconnected():
                break

            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg["type"] == "message":
                payload: dict = json.loads(msg["data"])
                yield f"data: {json.dumps(payload)}\n\n"
                if payload.get("node") in TERMINAL_NODES:
                    break
            else:
                now = asyncio.get_event_loop().time()
                if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    yield ": heartbeat\n\n"
                    last_heartbeat = now
    finally:
        await pubsub.unsubscribe(channel)
        await r.aclose()


@router.get("/{portfolio_id}/pdf")
def download_pdf(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate and return a PDF report for a completed portfolio."""
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
        .first()
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.status != "completed" or not portfolio.report:
        raise HTTPException(status_code=400, detail="Report not ready yet")

    from app.services.pdf_generator import generate_portfolio_pdf

    pdf_bytes = generate_portfolio_pdf(portfolio.report)
    filename = f"portai_report_{portfolio_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{portfolio_id}/save", status_code=status.HTTP_200_OK)
def save_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
        .first()
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return {"message": "Portfolio saved", "id": portfolio_id}
