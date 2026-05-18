"""API endpoints for the Deep Fundamental Analysis feature.

POST /api/v1/fundamental/analyze        → upload files, trigger pipeline
GET  /api/v1/fundamental/analyze/{id}   → poll result
GET  /api/v1/fundamental/history        → list past analyses
"""
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.agents.fundamental.graph import run_fundamental_pipeline
from app.agents.fundamental.state import FileInput
from app.api.deps import get_current_user
from app.database import get_db
from app.models.fundamental import FundamentalAnalysis, UploadedFile
from app.models.user import User
from app.services.storage import is_configured, upload_file

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".xlsx"}
MAX_FILE_SIZE_MB   = 50
MAX_FILES          = 3


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".xlsx":
        return "xlsx"
    raise ValueError(f"Unsupported file type: {ext}. Use .pdf or .xlsx")


async def _read_and_validate(upload: UploadFile) -> bytes:
    content = await upload.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{upload.filename} terlalu besar ({size_mb:.1f} MB). Maksimal {MAX_FILE_SIZE_MB} MB.",
        )
    return content


# ── POST /analyze ─────────────────────────────────────────────────────────────

@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
async def create_analysis(
    ticker:        str              = Form(..., description="Kode saham IDX, e.g. BBCA"),
    current_price: Optional[float]  = Form(None, description="Harga saham saat ini (opsional)"),
    years:         Optional[str]    = Form(None, description="Tahun per file, pisahkan koma: '2023,2022,2021'"),
    files:         List[UploadFile] = File(..., description="1–3 file PDF atau Excel laporan keuangan"),
    current_user:  User             = Depends(get_current_user),
    db:            Session          = Depends(get_db),
):
    """Upload financial statement files and run the fundamental analysis pipeline."""

    if not files or len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload 1–{MAX_FILES} file laporan keuangan.",
        )

    # Parse year hints
    year_hints: List[Optional[int]] = []
    if years:
        try:
            year_hints = [int(y.strip()) for y in years.split(",")]
        except ValueError:
            year_hints = []
    while len(year_hints) < len(files):
        year_hints.append(None)

    # Read & validate files
    file_inputs: List[FileInput]      = []
    upload_records: List[dict]        = []

    for i, upload in enumerate(files):
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{upload.filename}' tidak didukung. Gunakan .pdf atau .xlsx",
            )

        content   = await _read_and_validate(upload)
        file_type = _detect_file_type(upload.filename or "")

        file_inputs.append(FileInput(
            filename=upload.filename or f"file_{i}",
            content=content,
            file_type=file_type,
            year=year_hints[i],
        ))
        upload_records.append({
            "filename": upload.filename,
            "content":  content,
            "file_type": file_type,
            "year":     year_hints[i],
        })

    # Create DB record
    analysis = FundamentalAnalysis(
        user_id=current_user.id,
        ticker=ticker.upper(),
        current_price=current_price,
        status="processing",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Upload files to Supabase (if configured)
    if is_configured():
        for rec in upload_records:
            try:
                result = upload_file(
                    file_bytes=rec["content"],
                    filename=rec["filename"],
                    user_id=current_user.id,
                    analysis_id=analysis.id,
                )
                db_file = UploadedFile(
                    analysis_id=analysis.id,
                    file_name=rec["filename"],
                    file_url=result["public_url"],
                    storage_path=result["storage_path"],
                    file_type=rec["file_type"],
                    year=rec["year"],
                )
                db.add(db_file)
            except Exception as exc:
                logger.warning("Supabase upload failed for %s: %s", rec["filename"], exc)
        db.commit()

    # Run pipeline (in-process for now; swap to Celery task in production)
    try:
        final_state = await run_fundamental_pipeline(
            ticker=ticker,
            files=file_inputs,
            current_price=current_price,
        )

        analysis.extracted_data   = final_state.get("extracted_data")
        analysis.normalized_data  = [dict(y) for y in final_state.get("normalized_data", [])]
        analysis.ratios           = final_state.get("ratios")
        analysis.trend_analysis   = final_state.get("trend_analysis")
        analysis.red_flags        = final_state.get("red_flags")
        analysis.valuation        = final_state.get("valuation")
        analysis.entry_signal     = final_state.get("entry_signal")
        analysis.narrative_report = final_state.get("narrative_report")
        analysis.status           = "completed"
        analysis.completed_at     = datetime.now(timezone.utc)

    except Exception as exc:
        logger.error("Fundamental pipeline error: %s", exc)
        analysis.status        = "failed"
        analysis.error_message = str(exc)

    db.commit()
    db.refresh(analysis)

    return {
        "analysis_id": analysis.id,
        "status":      analysis.status,
        "ticker":      analysis.ticker,
    }


# ── GET /analyze/{id} ─────────────────────────────────────────────────────────

@router.get("/analyze/{analysis_id}")
def get_analysis(
    analysis_id:  int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    analysis = (
        db.query(FundamentalAnalysis)
        .filter(
            FundamentalAnalysis.id      == analysis_id,
            FundamentalAnalysis.user_id == current_user.id,
        )
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analisis tidak ditemukan.")

    return {
        "id":               analysis.id,
        "ticker":           analysis.ticker,
        "current_price":    float(analysis.current_price) if analysis.current_price else None,
        "status":           analysis.status,
        "error_message":    analysis.error_message,
        "ratios":           analysis.ratios,
        "trend_analysis":   analysis.trend_analysis,
        "red_flags":        analysis.red_flags,
        "valuation":        analysis.valuation,
        "entry_signal":     analysis.entry_signal,
        "narrative_report": analysis.narrative_report,
        "files":            [
            {"filename": f.file_name, "year": f.year, "type": f.file_type}
            for f in analysis.files
        ],
        "created_at":    analysis.created_at.isoformat(),
        "completed_at":  analysis.completed_at.isoformat() if analysis.completed_at else None,
    }


# ── GET /history ──────────────────────────────────────────────────────────────

@router.get("/history")
def get_history(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    analyses = (
        db.query(FundamentalAnalysis)
        .filter(FundamentalAnalysis.user_id == current_user.id)
        .order_by(FundamentalAnalysis.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id":           a.id,
            "ticker":       a.ticker,
            "status":       a.status,
            "score":        (a.entry_signal or {}).get("total_score"),
            "signal":       ((a.entry_signal or {}).get("signal") or {}).get("label"),
            "created_at":   a.created_at.isoformat(),
        }
        for a in analyses
    ]
