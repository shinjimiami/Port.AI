import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1 import auth, fundamental, market, portfolio

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)

app = FastAPI(
    title=settings.APP_NAME,
    description="AI Agent-powered Portfolio Recommendation Platform",
    version="1.0.0",
    # Hide docs in production
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api/v1/auth",        tags=["auth"])
app.include_router(portfolio.router,   prefix="/api/v1/portfolio",   tags=["portfolio"])
app.include_router(market.router,      prefix="/api/v1/market",      tags=["market"])
app.include_router(fundamental.router, prefix="/api/v1/fundamental", tags=["fundamental"])


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
