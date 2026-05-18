"""State schema for the Deep Fundamental Analysis LangGraph pipeline."""
from typing import Any, Dict, List, Optional, TypedDict


class FileInput(TypedDict):
    filename: str
    content: bytes       # raw file bytes (held in memory during pipeline only)
    file_type: str       # "pdf" | "xlsx"
    year: Optional[int]  # user-labeled year (2023, 2022, 2021 …)


class FinancialYear(TypedDict):
    year: int
    income_statement: Dict[str, Optional[float]]
    balance_sheet:    Dict[str, Optional[float]]
    cash_flow:        Dict[str, Optional[float]]


# ── Income Statement field keys ────────────────────────────────────────────
# revenue, gross_profit, operating_income, net_income, ebitda, eps,
# interest_expense

# ── Balance Sheet field keys ───────────────────────────────────────────────
# total_assets, current_assets, cash, total_liabilities, current_liabilities,
# total_equity, total_debt, inventory, accounts_receivable

# ── Cash Flow field keys ───────────────────────────────────────────────────
# operating_cash_flow, capex, free_cash_flow


class FundamentalState(TypedDict):
    # ── Inputs ────────────────────────────────────────────────────────────
    ticker:        str
    current_price: Optional[float]
    files:         List[FileInput]

    # ── Node outputs ──────────────────────────────────────────────────────
    extracted_data:   Dict[str, Any]          # FILE_EXTRACTOR: raw per-file data
    normalized_data:  List[FinancialYear]     # FILE_EXTRACTOR: sorted 3-yr list
    ratios:           Dict[str, Any]          # RATIO_CALCULATOR
    trend_analysis:   Dict[str, Any]          # TREND_ANALYZER
    red_flags:        List[Dict[str, Any]]    # RED_FLAG_DETECTOR
    valuation:        Dict[str, Any]          # VALUATION_ENGINE
    entry_signal:     Dict[str, Any]          # ENTRY_SIGNAL_SCORER
    narrative_report: str                     # NARRATIVE_GENERATOR

    errors: List[str]
