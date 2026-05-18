from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # User inputs
    budget = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="USD")
    horizon = Column(String(50), nullable=False)          # e.g. "6 months", "1 year"
    asset_classes = Column(JSON, nullable=False)           # ["US_STOCKS", "IDX", "CRYPTO"]
    risk_tolerance = Column(String(20), nullable=True)     # may be inferred

    # Agent outputs
    allocation_plan = Column(JSON, nullable=True)
    selected_assets = Column(JSON, nullable=True)
    report = Column(JSON, nullable=True)

    status = Column(
        Enum("pending", "processing", "completed", "failed", name="portfolio_status"),
        default="pending",
        nullable=False,
    )
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="portfolios")


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    asset_class = Column(String(50), nullable=False, index=True)  # "US_STOCKS" | "IDX" | "CRYPTO"
    data = Column(JSON, nullable=False)
    fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
