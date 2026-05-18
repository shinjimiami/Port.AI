from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class StockQuote(BaseModel):
    ticker: str
    name: str
    price: float
    change_pct_1d: Optional[float] = None
    change_pct_7d: Optional[float] = None
    change_pct_30d: Optional[float] = None
    sector: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    volume: Optional[float] = None
    currency: str = "USD"


class CryptoQuote(BaseModel):
    id: str
    symbol: str
    name: str
    price_usd: float
    change_pct_1d: Optional[float] = None
    change_pct_7d: Optional[float] = None
    change_pct_30d: Optional[float] = None
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    rank: Optional[int] = None


class MarketSnapshotResponse(BaseModel):
    asset_class: str
    data: Dict[str, Any]
    fetched_at: datetime

    model_config = {"from_attributes": True}
