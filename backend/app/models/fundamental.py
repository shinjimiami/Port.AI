from datetime import datetime, timezone

from sqlalchemy import (
    Column, DateTime, Enum, Float, ForeignKey,
    Integer, Numeric, String, Text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class FundamentalAnalysis(Base):
    __tablename__ = "fundamental_analyses"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # User inputs
    ticker        = Column(String(20), nullable=False, index=True)
    current_price = Column(Numeric(18, 4), nullable=True)

    # Agent pipeline outputs (each node stores its result here)
    extracted_data   = Column(JSONB, nullable=True)   # FILE_EXTRACTOR raw
    normalized_data  = Column(JSONB, nullable=True)   # FILE_EXTRACTOR structured
    ratios           = Column(JSONB, nullable=True)   # RATIO_CALCULATOR
    trend_analysis   = Column(JSONB, nullable=True)   # TREND_ANALYZER
    red_flags        = Column(JSONB, nullable=True)   # RED_FLAG_DETECTOR
    valuation        = Column(JSONB, nullable=True)   # VALUATION_ENGINE
    entry_signal     = Column(JSONB, nullable=True)   # ENTRY_SIGNAL_SCORER
    narrative_report = Column(Text, nullable=True)    # NARRATIVE_GENERATOR

    status        = Column(
        Enum("pending", "processing", "completed", "failed",
             name="fundamental_status"),
        default="pending",
        nullable=False,
    )
    error_message = Column(String, nullable=True)

    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at  = Column(DateTime(timezone=True), nullable=True)

    user  = relationship("User",   back_populates="fundamental_analyses")
    files = relationship("UploadedFile", back_populates="analysis",
                         cascade="all, delete-orphan")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id          = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("fundamental_analyses.id", ondelete="CASCADE"),
                         nullable=False, index=True)

    file_name   = Column(String(255), nullable=False)
    file_url    = Column(Text, nullable=False)          # Supabase public/signed URL
    storage_path = Column(Text, nullable=False)         # internal Supabase bucket path
    file_type   = Column(Enum("pdf", "xlsx", name="file_type_enum"), nullable=False)
    year        = Column(Integer, nullable=True)         # e.g. 2023, 2022, 2021

    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    analysis = relationship("FundamentalAnalysis", back_populates="files")
