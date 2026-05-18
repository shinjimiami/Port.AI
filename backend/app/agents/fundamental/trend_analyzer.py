"""Node 3 — TREND_ANALYZER
Pure Python. No LLM.
Calculates YoY growth, CAGR, margin trends, and detects key patterns.
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.fundamental.state import FinancialYear, FundamentalState

logger = logging.getLogger(__name__)


def _yoy(old: Optional[float], new: Optional[float]) -> Optional[float]:
    if old is None or new is None or old == 0:
        return None
    return round((new - old) / abs(old) * 100, 2)


def _cagr(start: Optional[float], end: Optional[float], years: int) -> Optional[float]:
    if start is None or end is None or start <= 0 or years <= 0:
        return None
    try:
        return round(((end / start) ** (1 / years) - 1) * 100, 2)
    except Exception:
        return None


def _classify(values: List[Optional[float]]) -> str:
    """Classify a growth rate series."""
    clean = [v for v in values if v is not None]
    if len(clean) < 2:
        return "INSUFFICIENT_DATA"
    if all(v < 0 for v in clean):
        return "DECLINING"
    if all(v > 0 for v in clean):
        if clean[-1] > clean[0]:
            return "ACCELERATING"
        if clean[-1] < clean[0]:
            return "DECELERATING"
        return "STABLE"
    return "VOLATILE"


def _margin_trend(margins: List[Optional[float]]) -> str:
    clean = [v for v in margins if v is not None]
    if len(clean) < 2:
        return "INSUFFICIENT_DATA"
    if clean[-1] > clean[0] + 1:
        return "EXPANDING"
    if clean[-1] < clean[0] - 1:
        return "COMPRESSING"
    return "STABLE"


async def trend_analyzer_node(state: FundamentalState) -> FundamentalState:
    normalized: List[FinancialYear] = state["normalized_data"]
    ratios_data: Dict[str, Any]     = state.get("ratios", {})
    errors = list(state.get("errors", []))

    if len(normalized) < 2:
        errors.append("TrendAnalyzer: need at least 2 years of data for trend analysis.")
        return {**state, "trend_analysis": {}, "errors": errors}

    # Sort ascending
    years = sorted(normalized, key=lambda y: y["year"])
    n = len(years)

    def get_field(section: str, field: str) -> List[Optional[float]]:
        return [y[section].get(field) for y in years]  # type: ignore[literal-required]

    # ── Revenue ───────────────────────────────────────────────────────────
    revenues = get_field("income_statement", "revenue")
    rev_yoy = [_yoy(revenues[i], revenues[i + 1]) for i in range(n - 1)]
    rev_cagr = _cagr(revenues[0], revenues[-1], n - 1)

    # ── Net Income ────────────────────────────────────────────────────────
    ni_vals = get_field("income_statement", "net_income")
    ni_yoy  = [_yoy(ni_vals[i], ni_vals[i + 1]) for i in range(n - 1)]
    ni_cagr = _cagr(ni_vals[0], ni_vals[-1], n - 1)

    # ── EPS ───────────────────────────────────────────────────────────────
    eps_vals = get_field("income_statement", "eps")
    eps_yoy  = [_yoy(eps_vals[i], eps_vals[i + 1]) for i in range(n - 1)]

    # ── FCF ───────────────────────────────────────────────────────────────
    fcf_vals = get_field("cash_flow", "free_cash_flow")
    fcf_yoy  = [_yoy(fcf_vals[i], fcf_vals[i + 1]) for i in range(n - 1)]

    # ── Margin trends (from ratios) ────────────────────────────────────────
    ratios_years = ratios_data.get("years", [])

    def get_ratio(field: str, section: str) -> List[Optional[float]]:
        return [ry.get(section, {}).get(field) for ry in ratios_years]

    gross_margins = get_ratio("gross_margin_pct", "profitability")
    net_margins   = get_ratio("net_margin_pct",   "profitability")
    op_margins    = get_ratio("operating_margin_pct", "profitability")

    # ── Debt trend ────────────────────────────────────────────────────────
    debt_vals = get_field("balance_sheet", "total_debt")
    debt_yoy  = [_yoy(debt_vals[i], debt_vals[i + 1]) for i in range(n - 1)]

    # ── Pattern detection ─────────────────────────────────────────────────
    patterns: List[str] = []

    # Revenue growing but margin compressing
    if (all(v is not None and v > 0 for v in rev_yoy) and
            _margin_trend(gross_margins) == "COMPRESSING"):
        patterns.append("Revenue tumbuh namun gross margin menyempit — tekanan persaingan atau kenaikan biaya.")

    # Net income growing but FCF flat/declining
    if (all(v is not None and v > 0 for v in ni_yoy) and
            len([v for v in fcf_yoy if v is not None and v <= 0]) >= (n - 1) // 2 + 1):
        patterns.append("Laba bersih tumbuh namun FCF stagnan/menurun — kualitas laba perlu diwaspadai.")

    # Debt growing faster than revenue (2+ periods)
    fast_debt_count = sum(
        1 for d, r in zip(debt_yoy, rev_yoy)
        if d is not None and r is not None and d > r
    )
    if fast_debt_count >= 2:
        patterns.append("Utang tumbuh lebih cepat dari pendapatan selama ≥2 periode — risiko leverage meningkat.")

    # Declining margin 3 consecutive years
    if len(net_margins) >= 3:
        clean_nm = [v for v in net_margins if v is not None]
        if len(clean_nm) >= 3 and all(clean_nm[i] > clean_nm[i + 1] for i in range(len(clean_nm) - 1)):
            patterns.append("Net margin menurun 3 tahun berturut-turut — tren profitabilitas memburuk.")

    trend_analysis = {
        "year_labels":   [y["year"] for y in years],
        "revenue": {
            "values":   revenues,
            "yoy_pct":  rev_yoy,
            "cagr_pct": rev_cagr,
            "trend":    _classify(rev_yoy),
        },
        "net_income": {
            "values":   ni_vals,
            "yoy_pct":  ni_yoy,
            "cagr_pct": ni_cagr,
            "trend":    _classify(ni_yoy),
        },
        "eps": {
            "values":  eps_vals,
            "yoy_pct": eps_yoy,
            "trend":   _classify(eps_yoy),
        },
        "free_cash_flow": {
            "values":  fcf_vals,
            "yoy_pct": fcf_yoy,
            "trend":   _classify(fcf_yoy),
        },
        "margins": {
            "gross_margin_pct":     gross_margins,
            "operating_margin_pct": op_margins,
            "net_margin_pct":       net_margins,
            "gross_trend":          _margin_trend(gross_margins),
            "net_trend":            _margin_trend(net_margins),
        },
        "debt": {
            "values":  debt_vals,
            "yoy_pct": debt_yoy,
        },
        "detected_patterns": patterns,
    }

    logger.info("TrendAnalyzer: %d patterns detected", len(patterns))
    return {**state, "trend_analysis": trend_analysis, "errors": errors}
