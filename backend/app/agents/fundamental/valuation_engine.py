"""Node 5 — VALUATION_ENGINE
Pure Python. No LLM.
DCF + relative valuation. Only runs if current_price is provided.
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.fundamental.state import FinancialYear, FundamentalState

logger = logging.getLogger(__name__)

WACC            = 0.12   # 12% discount rate (IDX WACC assumption)
TERMINAL_GROWTH = 0.04   # 4% Indonesia long-term GDP
DCF_YEARS       = 5
MAX_FCF_GROWTH  = 0.15   # cap growth rate at 15%

# Currency detection: IDX companies that report in USD have EPS << 1
# while their IDR share price >> 100. We apply this approximate rate.
IDR_PER_USD = 16_000

# IDX sector P/E benchmarks
SECTOR_PE = {
    "banking":        (8,  15),
    "consumer":       (15, 25),
    "technology":     (20, 40),
    "infrastructure": (10, 18),
    "energy":         (8,  14),
    "industrial":     (10, 16),
    "property":       (8,  15),
    "default":        (10, 20),
}

VALUATION_ZONES = [
    (0.70, "DEEPLY_UNDERVALUED",        "🟢 Sangat Murah (<70% nilai wajar)"),
    (0.90, "UNDERVALUED",               "🟢 Murah (70–90% nilai wajar)"),
    (1.10, "FAIRLY_VALUED",             "🟡 Wajar (90–110% nilai wajar)"),
    (1.30, "OVERVALUED",                "🟠 Mahal (110–130% nilai wajar)"),
    (9999, "SIGNIFICANTLY_OVERVALUED",  "🔴 Sangat Mahal (>130% nilai wajar)"),
]


def _dcf_intrinsic(
    base_fcf: float,
    growth_rate: float,
    shares: Optional[float],
) -> Optional[float]:
    """Simple 5-year DCF → intrinsic value per share (if shares known)."""
    g = min(growth_rate, MAX_FCF_GROWTH)
    pv_fcfs = 0.0
    for t in range(1, DCF_YEARS + 1):
        projected = base_fcf * ((1 + g) ** t)
        pv_fcfs  += projected / ((1 + WACC) ** t)

    terminal_fcf = base_fcf * ((1 + g) ** DCF_YEARS) * (1 + TERMINAL_GROWTH)
    terminal_val = terminal_fcf / (WACC - TERMINAL_GROWTH)
    pv_terminal  = terminal_val / ((1 + WACC) ** DCF_YEARS)

    total_value = pv_fcfs + pv_terminal
    if shares and shares > 0:
        return total_value / shares
    return None


def _valuation_zone(price: float, intrinsic: float) -> Dict[str, str]:
    ratio = price / intrinsic
    for threshold, key, label in VALUATION_ZONES:
        if ratio <= threshold:
            return {"key": key, "label": label, "price_to_intrinsic": round(ratio, 3)}
    return {"key": "SIGNIFICANTLY_OVERVALUED",
            "label": VALUATION_ZONES[-1][2],
            "price_to_intrinsic": round(ratio, 3)}


async def valuation_engine_node(state: FundamentalState) -> FundamentalState:
    current_price: Optional[float] = state.get("current_price")
    normalized:    List[FinancialYear] = state["normalized_data"]
    trend:         Dict[str, Any]      = state.get("trend_analysis", {})
    errors = list(state.get("errors", []))

    if not current_price:
        logger.info("ValuationEngine: skipped — no current_price provided")
        return {**state, "valuation": {"skipped": True}, "errors": errors}

    if not normalized:
        errors.append("ValuationEngine: no financial data.")
        return {**state, "valuation": {}, "errors": errors}

    years_sorted = sorted(normalized, key=lambda y: y["year"])
    latest       = years_sorted[-1]

    # ── FCF base (average of last 2 years) ───────────────────────────────
    fcf_vals = [y["cash_flow"].get("free_cash_flow") for y in years_sorted[-2:]]
    fcf_vals = [v for v in fcf_vals if v is not None and v > 0]
    base_fcf  = sum(fcf_vals) / len(fcf_vals) if fcf_vals else None

    # ── Growth rate from revenue CAGR ────────────────────────────────────
    rev_cagr = trend.get("revenue", {}).get("cagr_pct")
    growth   = min((rev_cagr or 6) / 100, MAX_FCF_GROWTH)

    # ── Shares outstanding (derive from EPS + net income if available) ────
    eps = latest["income_statement"].get("eps")
    ni  = latest["income_statement"].get("net_income")
    shares: Optional[float] = None
    if eps and ni and eps != 0:
        shares = ni / eps

    # ── Currency detection ────────────────────────────────────────────────
    # IDX companies reporting in USD have EPS in cents (< 5) while their
    # IDR share price > 100. Detect and convert intrinsic to IDR.
    is_usd_report = bool(eps and eps < 5.0 and current_price > 100)
    fx_rate = IDR_PER_USD if is_usd_report else 1.0

    # ── DCF valuation ─────────────────────────────────────────────────────
    dcf_value_raw: Optional[float] = None     # in report currency
    dcf_value_idr: Optional[float] = None     # always IDR (for comparison)
    if base_fcf and base_fcf > 0:
        dcf_value_raw = _dcf_intrinsic(base_fcf, growth, shares)
        if dcf_value_raw:
            dcf_value_idr = dcf_value_raw * fx_rate

    # ── Relative valuation (P/E, P/BV) ────────────────────────────────────
    pe_current: Optional[float] = None
    pbv_current: Optional[float] = None

    eps_idr = eps * fx_rate if eps else None  # eps converted to IDR for display
    if eps_idr and eps_idr > 0:
        pe_current = round(current_price / eps_idr, 2)

    equity = latest["balance_sheet"].get("total_equity")
    if equity and shares and shares > 0:
        bvps_idr = (equity / shares) * fx_rate
        if bvps_idr > 0:
            pbv_current = round(current_price / bvps_idr, 2)

    # ── Zone classification ────────────────────────────────────────────────
    zone: Optional[Dict[str, Any]] = None
    if dcf_value_idr and dcf_value_idr > 0:
        zone = _valuation_zone(current_price, dcf_value_idr)

    valuation = {
        "current_price": current_price,
        "is_usd_report": is_usd_report,
        "dcf": {
            "base_fcf":        base_fcf,
            "growth_rate_pct": round(growth * 100, 2),
            "wacc_pct":        WACC * 100,
            "terminal_growth_pct": TERMINAL_GROWTH * 100,
            "intrinsic_value_per_share": round(dcf_value_idr) if dcf_value_idr else None,
        },
        "relative": {
            "pe_current":   pe_current,
            "pbv_current":  pbv_current,
            "eps_latest":   round(eps_idr) if eps_idr else eps,
        },
        "zone": zone,
        "skipped": False,
    }

    logger.info("ValuationEngine: DCF intrinsic=%.0f (IDR), zone=%s%s",
                dcf_value_idr or 0, zone.get("key") if zone else "N/A",
                " [USD report, fx=16000]" if is_usd_report else "")
    return {**state, "valuation": valuation, "errors": errors}
