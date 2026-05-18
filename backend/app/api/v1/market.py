import asyncio
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User
from app.services.market_data.ai_brief import generate_ai_brief
from app.services.market_data.crypto import fetch_crypto
from app.services.market_data.fear_greed import fetch_fear_greed
from app.services.market_data.idx_stocks import fetch_idx_stocks
from app.services.market_data.indices import fetch_indices
from app.services.market_data.market_sentiment import fetch_market_sentiment
from app.services.market_data.news import fetch_market_news
from app.services.market_data.us_stocks import fetch_us_stocks

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Legacy snapshot endpoints ─────────────────────────────────────────────────

@router.get("/snapshot")
async def market_snapshot(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Return a live market overview across all asset classes."""
    try:
        us_data, crypto_data = await asyncio.gather(fetch_us_stocks(), fetch_crypto(top_n=30))
        idx_data = fetch_idx_stocks()
        return {"US_STOCKS": us_data, "IDX": idx_data, "CRYPTO": crypto_data}
    except Exception as exc:
        logger.error("Market snapshot failed: %s", exc)
        raise HTTPException(status_code=503, detail="Market data temporarily unavailable")


@router.get("/snapshot/{asset_class}")
async def asset_class_snapshot(
    asset_class: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return market data for a single asset class."""
    asset_class = asset_class.upper()
    try:
        if asset_class == "US_STOCKS":
            return {"asset_class": asset_class, "data": await fetch_us_stocks()}
        elif asset_class == "IDX":
            return {"asset_class": asset_class, "data": fetch_idx_stocks()}
        elif asset_class == "CRYPTO":
            return {"asset_class": asset_class, "data": await fetch_crypto()}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown asset class: {asset_class}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Asset snapshot failed for %s: %s", asset_class, exc)
        raise HTTPException(status_code=503, detail="Market data temporarily unavailable")


# ── Dashboard endpoints ───────────────────────────────────────────────────────

@router.get("/fear-greed")
async def fear_greed(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Return current Fear & Greed Index (alternative.me). Cached 1 h."""
    try:
        return await fetch_fear_greed()
    except Exception as exc:
        logger.error("Fear & Greed endpoint failed: %s", exc)
        raise HTTPException(status_code=503, detail="Fear & Greed data unavailable")


@router.get("/news")
async def market_news(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Return latest market news. Cached 15 min."""
    try:
        articles = await fetch_market_news()
        return {"articles": articles, "count": len(articles)}
    except Exception as exc:
        logger.error("Market news endpoint failed: %s", exc)
        raise HTTPException(status_code=503, detail="News data unavailable")


@router.get("/indices")
async def market_indices(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Return live index prices (S&P, NASDAQ, JKSE, BTC, ETH, Gold). Cached 5 min."""
    try:
        data = await fetch_indices()
        return {"indices": data}
    except Exception as exc:
        logger.error("Indices endpoint failed: %s", exc)
        raise HTTPException(status_code=503, detail="Indices data unavailable")


@router.get("/sentiment")
async def market_sentiment(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Return intraday market sentiment from live CoinGecko data. Cached 60 s."""
    try:
        return await fetch_market_sentiment()
    except Exception as exc:
        logger.error("Market sentiment endpoint failed: %s", exc)
        raise HTTPException(status_code=503, detail="Market sentiment unavailable")


@router.get("/ai-brief")
async def ai_market_brief(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Return AI-generated market brief (Claude). Cached 1 h."""
    try:
        fear_greed_data, indices_data, news_data = await asyncio.gather(
            fetch_fear_greed(),
            fetch_indices(),
            fetch_market_news(),
        )
        return await generate_ai_brief(fear_greed_data, indices_data, news_data)
    except Exception as exc:
        logger.error("AI brief endpoint failed: %s", exc)
        raise HTTPException(status_code=503, detail="AI brief unavailable")


@router.get("/dashboard")
async def market_dashboard(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Aggregate endpoint: fear-greed + sentiment + indices + news."""
    try:
        fear_greed_data, sentiment_data, indices_data, news_data = await asyncio.gather(
            fetch_fear_greed(),
            fetch_market_sentiment(),
            fetch_indices(),
            fetch_market_news(),
        )
        return {
            "fear_greed": fear_greed_data,
            "sentiment": sentiment_data,
            "indices": indices_data,
            "news": news_data,
        }
    except Exception as exc:
        logger.error("Dashboard endpoint failed: %s", exc)
        raise HTTPException(status_code=503, detail="Dashboard data temporarily unavailable")
