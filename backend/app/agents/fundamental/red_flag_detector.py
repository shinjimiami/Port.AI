"""Node 4 — RED_FLAG_DETECTOR
Pure Python. No LLM.
Scans ratios and trends for accounting anomalies and risk signals.
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.fundamental.state import FundamentalState

logger = logging.getLogger(__name__)

HIGH   = "HIGH"
MEDIUM = "MEDIUM"
LOW    = "LOW"


def _flag(severity: str, category: str, description: str) -> Dict[str, str]:
    return {"severity": severity, "category": category, "description": description}


def _get_ratio_series(ratios_years: List[dict], section: str, field: str) -> List[Optional[float]]:
    return [ry.get(section, {}).get(field) for ry in ratios_years]


async def red_flag_detector_node(state: FundamentalState) -> FundamentalState:
    ratios_data:    Dict[str, Any] = state.get("ratios", {})
    trend_analysis: Dict[str, Any] = state.get("trend_analysis", {})
    normalized                     = state["normalized_data"]
    errors = list(state.get("errors", []))

    flags: List[Dict[str, str]] = []
    ratios_years: List[dict]    = ratios_data.get("years", [])
    n = len(ratios_years)

    if n == 0:
        return {**state, "red_flags": [], "errors": errors}

    # ── EARNINGS QUALITY ──────────────────────────────────────────────────

    ccr_series = _get_ratio_series(ratios_years, "cash_quality", "cash_conversion_ratio")
    low_ccr_count = sum(1 for v in ccr_series if v is not None and v < 0.7)
    if low_ccr_count >= 2:
        flags.append(_flag(HIGH, "Earnings Quality",
            f"Cash Conversion Ratio < 0.7 selama {low_ccr_count} tahun — "
            "laba bersih tidak terkonversi menjadi kas secara memadai."))
    elif any(v is not None and v < 0.7 for v in ccr_series):
        flags.append(_flag(MEDIUM, "Earnings Quality",
            "Cash Conversion Ratio < 0.7 pada salah satu tahun — perlu dimonitor."))

    # Receivables growing 2x faster than revenue
    years_sorted = sorted(normalized, key=lambda y: y["year"])
    if len(years_sorted) >= 2:
        rev_growth_rates  = []
        ar_growth_rates   = []
        for i in range(len(years_sorted) - 1):
            old_rev = years_sorted[i]["income_statement"].get("revenue")
            new_rev = years_sorted[i + 1]["income_statement"].get("revenue")
            old_ar  = years_sorted[i]["balance_sheet"].get("accounts_receivable")
            new_ar  = years_sorted[i + 1]["balance_sheet"].get("accounts_receivable")
            if old_rev and new_rev and old_rev != 0:
                rev_growth_rates.append((new_rev - old_rev) / abs(old_rev))
            if old_ar and new_ar and old_ar != 0:
                ar_growth_rates.append((new_ar - old_ar) / abs(old_ar))

        fast_ar = sum(
            1 for ag, rg in zip(ar_growth_rates, rev_growth_rates)
            if ag > rg * 2
        )
        if fast_ar >= 2:
            flags.append(_flag(HIGH, "Earnings Quality",
                "Piutang tumbuh >2x lebih cepat dari pendapatan selama ≥2 periode — "
                "indikasi pengakuan pendapatan agresif."))
        elif fast_ar == 1:
            flags.append(_flag(MEDIUM, "Earnings Quality",
                "Piutang tumbuh jauh lebih cepat dari pendapatan — perlu diwaspadai."))

    # ── LEVERAGE RISK ─────────────────────────────────────────────────────

    der_series = _get_ratio_series(ratios_years, "solvency", "der")
    high_der   = [v for v in der_series if v is not None and v > 2.0]
    if len(high_der) >= 2:
        trend_up = (der_series[-1] or 0) > (der_series[0] or 0)
        sev = HIGH if trend_up else MEDIUM
        flags.append(_flag(sev, "Leverage Risk",
            f"DER > 2.0 selama {len(high_der)} tahun"
            + (" dan terus meningkat" if trend_up else "") +
            " — risiko refinancing dan tekanan bunga tinggi."))

    ic_series = _get_ratio_series(ratios_years, "solvency", "interest_coverage")
    low_ic = [v for v in ic_series if v is not None and v < 2.0]
    if len(low_ic) >= 2:
        flags.append(_flag(HIGH, "Leverage Risk",
            f"Interest Coverage < 2.0 selama {len(low_ic)} tahun — "
            "laba operasi hampir tidak cukup menutup beban bunga."))
    elif len(low_ic) == 1:
        flags.append(_flag(MEDIUM, "Leverage Risk",
            "Interest Coverage < 2.0 pada salah satu tahun — tekanan bunga signifikan."))

    # Debt growing faster than revenue
    debt_trend   = trend_analysis.get("debt", {}).get("yoy_pct", [])
    rev_trend_yy = trend_analysis.get("revenue", {}).get("yoy_pct", [])
    debt_faster  = sum(
        1 for d, r in zip(debt_trend, rev_trend_yy)
        if d is not None and r is not None and d > r
    )
    if debt_faster >= 2:
        flags.append(_flag(MEDIUM, "Leverage Risk",
            "Utang tumbuh lebih cepat dari pendapatan selama ≥2 periode — "
            "perusahaan menggunakan leverage untuk mendanai operasi/ekspansi."))

    # ── PROFITABILITY ─────────────────────────────────────────────────────

    gm_trend = trend_analysis.get("margins", {}).get("gross_trend")
    if gm_trend == "COMPRESSING":
        flags.append(_flag(MEDIUM, "Profitability",
            "Gross margin menyempit secara konsisten — daya saing harga atau "
            "kontrol biaya pokok melemah."))

    op_margins = _get_ratio_series(ratios_years, "profitability", "operating_margin_pct")
    thin_op = [v for v in op_margins if v is not None and v < 5.0]
    if len(thin_op) >= 2:
        flags.append(_flag(MEDIUM, "Profitability",
            f"Operating margin < 5% selama {len(thin_op)} tahun — bisnis dengan margin tipis "
            "rentan terhadap guncangan biaya atau permintaan."))

    # ── CASH FLOW ────────────────────────────────────────────────────────

    fcf_vals = [y["cash_flow"].get("free_cash_flow") for y in years_sorted]
    neg_fcf  = [v for v in fcf_vals if v is not None and v < 0]
    if len(neg_fcf) >= 2:
        flags.append(_flag(HIGH, "Cash Flow",
            f"Free Cash Flow negatif selama {len(neg_fcf)} tahun — perusahaan mengkonsumsi "
            "lebih banyak kas daripada yang dihasilkan."))

    ocf_series   = [y["cash_flow"].get("operating_cash_flow") for y in years_sorted]
    capex_series = [y["cash_flow"].get("capex") for y in years_sorted]
    capex_over_ocf = sum(
        1 for ocf, cap in zip(ocf_series, capex_series)
        if ocf is not None and cap is not None and abs(cap) > abs(ocf)
    )
    if capex_over_ocf >= 2:
        flags.append(_flag(MEDIUM, "Cash Flow",
            f"CAPEX melebihi Operating Cash Flow selama {capex_over_ocf} tahun — "
            "fase investasi berat, perlu dimonitor apakah menghasilkan ROI."))

    logger.info("RedFlagDetector: %d flag(s) found", len(flags))
    return {**state, "red_flags": flags, "errors": errors}
