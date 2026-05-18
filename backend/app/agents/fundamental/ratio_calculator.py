"""Node 2 — RATIO_CALCULATOR
Pure Python. No LLM needed.
Calculates all financial ratios for each year in normalized_data.
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.fundamental.state import FinancialYear, FundamentalState

logger = logging.getLogger(__name__)


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    return round(a / b, 6)


def _pct(a: Optional[float], b: Optional[float]) -> Optional[float]:
    v = _safe_div(a, b)
    return round(v * 100, 4) if v is not None else None


def _calc_year_ratios(y: FinancialYear) -> Dict[str, Any]:
    IS = y["income_statement"]
    BS = y["balance_sheet"]
    CF = y["cash_flow"]

    rev  = IS.get("revenue")
    gp   = IS.get("gross_profit")
    oi   = IS.get("operating_income")
    ni   = IS.get("net_income")
    ebit = oi  # treat operating_income as EBIT proxy
    int_exp = IS.get("interest_expense")
    ebitda  = IS.get("ebitda")

    ta   = BS.get("total_assets")
    ca   = BS.get("current_assets")
    cash = BS.get("cash")
    tl   = BS.get("total_liabilities")
    cl   = BS.get("current_liabilities")
    eq   = BS.get("total_equity")
    debt = BS.get("total_debt")
    inv  = BS.get("inventory")
    ar   = BS.get("accounts_receivable")

    ocf  = CF.get("operating_cash_flow")
    capex= CF.get("capex")
    fcf  = CF.get("free_cash_flow")

    # Derive FCF if missing
    if fcf is None and ocf is not None and capex is not None:
        fcf = ocf - abs(capex)

    # ── Profitability ─────────────────────────────────────────────────────
    gross_margin    = _pct(gp, rev)
    operating_margin= _pct(oi, rev)
    net_margin      = _pct(ni, rev)
    roe             = _pct(ni, eq)
    roa             = _pct(ni, ta)

    # ROIC = EBIT*(1-tax) / (equity + debt); assume effective tax ~22% for IDX
    nopat = (ebit * 0.78) if ebit is not None else None
    invested_capital = None
    if eq is not None and debt is not None:
        invested_capital = eq + debt
    roic = _pct(nopat, invested_capital)

    # ── Liquidity ─────────────────────────────────────────────────────────
    current_ratio = _safe_div(ca, cl)
    if current_ratio is not None:
        current_ratio = round(current_ratio, 4)

    quick_assets = None
    if ca is not None and inv is not None:
        quick_assets = ca - inv
    elif ca is not None:
        quick_assets = ca  # no inventory data, use current assets
    quick_ratio = _safe_div(quick_assets, cl)
    if quick_ratio is not None:
        quick_ratio = round(quick_ratio, 4)

    cash_ratio = _safe_div(cash, cl)
    if cash_ratio is not None:
        cash_ratio = round(cash_ratio, 4)

    # ── Solvency ──────────────────────────────────────────────────────────
    der = _safe_div(debt, eq)
    if der is not None:
        der = round(der, 4)
    debt_to_assets = _safe_div(debt, ta)
    if debt_to_assets is not None:
        debt_to_assets = round(debt_to_assets, 4)
    interest_coverage = _safe_div(ebit, int_exp)
    if interest_coverage is not None:
        interest_coverage = round(interest_coverage, 2)

    # ── Efficiency ────────────────────────────────────────────────────────
    asset_turnover = _safe_div(rev, ta)
    if asset_turnover is not None:
        asset_turnover = round(asset_turnover, 4)
    receivables_turnover = _safe_div(rev, ar)
    if receivables_turnover is not None:
        receivables_turnover = round(receivables_turnover, 4)

    # ── Cash Quality ──────────────────────────────────────────────────────
    cash_conversion = _safe_div(ocf, ni)
    if cash_conversion is not None:
        cash_conversion = round(cash_conversion, 4)
    fcf_margin = _pct(fcf, rev)
    capex_intensity = _pct(capex, rev) if capex is not None else None

    return {
        "year": y["year"],
        "profitability": {
            "gross_margin_pct":     gross_margin,
            "operating_margin_pct": operating_margin,
            "net_margin_pct":       net_margin,
            "roe_pct":              roe,
            "roa_pct":              roa,
            "roic_pct":             roic,
        },
        "liquidity": {
            "current_ratio":        current_ratio,
            "quick_ratio":          quick_ratio,
            "cash_ratio":           cash_ratio,
        },
        "solvency": {
            "der":                  der,
            "debt_to_assets":       debt_to_assets,
            "interest_coverage":    interest_coverage,
        },
        "efficiency": {
            "asset_turnover":       asset_turnover,
            "receivables_turnover": receivables_turnover,
        },
        "cash_quality": {
            "cash_conversion_ratio": cash_conversion,
            "fcf_margin_pct":        fcf_margin,
            "capex_intensity_pct":   capex_intensity,
        },
    }


async def ratio_calculator_node(state: FundamentalState) -> FundamentalState:
    normalized: List[FinancialYear] = state["normalized_data"]
    errors = list(state.get("errors", []))

    if not normalized:
        errors.append("RatioCalculator: no normalized data available.")
        return {**state, "ratios": {}, "errors": errors}

    ratios_by_year = [_calc_year_ratios(y) for y in normalized]

    ratios = {
        "years": ratios_by_year,
        "latest_year": ratios_by_year[-1] if ratios_by_year else {},
    }

    logger.info("RatioCalculator: calculated ratios for %d year(s)", len(ratios_by_year))
    return {**state, "ratios": ratios, "errors": errors}
