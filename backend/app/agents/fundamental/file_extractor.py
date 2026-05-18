"""Node 1 — FILE_EXTRACTOR
Extracts raw financial data from uploaded PDF / Excel files.

Strategy:
  PDF  → pdfplumber scans for financial statement sections by keyword,
          then Groq LLM parses the relevant pages into structured JSON.
  Excel → openpyxl/pandas identifies financial sheets by name/header,
          then Groq LLM maps rows to standard field names.

One LLM call per file keeps Groq usage minimal.
"""
import io
import json
import logging
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.fundamental.state import FileInput, FinancialYear, FundamentalState
from app.agents.llm import build_llm

logger = logging.getLogger(__name__)

# ── Keyword sets for section detection ────────────────────────────────────────

_IS_KEYWORDS = {
    "laporan laba rugi", "laba rugi komprehensif", "income statement",
    "profit or loss", "profit and loss", "pendapatan", "revenue",
    "laba bersih", "net income", "net profit",
}
_BS_KEYWORDS = {
    "laporan posisi keuangan", "neraca", "balance sheet",
    "total aset", "total assets", "ekuitas", "equity",
    "kewajiban", "liabilities",
}
_CF_KEYWORDS = {
    "laporan arus kas", "arus kas", "cash flow",
    "aktivitas operasi", "operating activities",
    "aktivitas investasi", "investing activities",
}

_ALL_FIN_KEYWORDS = _IS_KEYWORDS | _BS_KEYWORDS | _CF_KEYWORDS

# ── LLM system prompt ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a financial data extraction expert specializing in
Indonesian (IDX) and international annual reports.

You will receive raw text extracted from a financial statement document
(may be in Bahasa Indonesia or English, or mixed).

Your job: extract the key financial figures for ALL years present in the text
and return them as a JSON array. Each element represents one fiscal year.

Return ONLY a valid JSON array — no markdown, no explanation — in this exact schema:

[
  {
    "year": <4-digit integer>,
    "income_statement": {
      "revenue": <number or null>,
      "gross_profit": <number or null>,
      "operating_income": <number or null>,
      "net_income": <number or null>,
      "ebitda": <number or null>,
      "eps": <number or null>,
      "interest_expense": <number or null>
    },
    "balance_sheet": {
      "total_assets": <number or null>,
      "current_assets": <number or null>,
      "cash": <number or null>,
      "total_liabilities": <number or null>,
      "current_liabilities": <number or null>,
      "total_equity": <number or null>,
      "total_debt": <number or null>,
      "inventory": <number or null>,
      "accounts_receivable": <number or null>
    },
    "cash_flow": {
      "operating_cash_flow": <number or null>,
      "capex": <number or null>,
      "free_cash_flow": <number or null>
    }
  }
]

Rules:
- All monetary values must be in their ORIGINAL unit (do not convert).
  If the document says "dalam jutaan Rupiah" (in millions IDR), keep them
  as millions — do NOT multiply. Record the unit in your mind only.
- capex should be a POSITIVE number even if shown as negative in cash flow.
- free_cash_flow = operating_cash_flow - capex (calculate if not shown).
- If EBITDA is not stated, leave it null.
- If a field is genuinely missing or unreadable, use null.
- If multiple years appear (comparative statements), include all of them.
- eps (Earnings Per Share / Laba Per Saham Dasar) — use the basic figure.
- year: use the fiscal year end year (e.g. "31 Desember 2023" → 2023).
"""


# ── Public node ───────────────────────────────────────────────────────────────

async def file_extractor_node(state: FundamentalState) -> FundamentalState:
    files:  List[FileInput] = state["files"]
    errors: List[str]       = list(state.get("errors", []))
    ticker: str             = state["ticker"]

    if not files:
        raise ValueError("No files provided for extraction.")

    all_year_data: List[FinancialYear] = []
    raw_extractions: List[dict]        = []

    for f in files:
        logger.info("Extracting %s (%s)", f["filename"], f["file_type"])
        try:
            if f["file_type"] == "pdf":
                text = _extract_text_from_pdf(f["content"])
            else:
                text = _extract_text_from_excel(f["content"])

            if not text.strip():
                errors.append(f"{f['filename']}: could not read any text.")
                continue

            years = await _llm_parse(text, ticker, f.get("year"))
            if not years:
                errors.append(f"{f['filename']}: LLM returned no data.")
                continue

            raw_extractions.append({"filename": f["filename"], "years": years})
            all_year_data.extend(years)

        except Exception as exc:
            logger.error("Extraction failed for %s: %s", f["filename"], exc)
            errors.append(f"{f['filename']}: extraction error — {exc}")

    if not all_year_data:
        detail = "; ".join(errors) if errors else "unknown error"
        raise ValueError(
            f"Could not extract financial data from any file. "
            f"Details: {detail}"
        )

    normalized = _deduplicate_and_sort(all_year_data)
    logger.info("FileExtractor: extracted %d year(s) of data", len(normalized))

    return {
        **state,
        "extracted_data": {"files": raw_extractions},
        "normalized_data": normalized,
        "errors": errors,
    }


# ── PDF helpers ───────────────────────────────────────────────────────────────

def _extract_text_from_pdf(content: bytes) -> str:
    import pdfplumber

    relevant_pages: List[str] = []
    all_pages:      List[str] = []

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""

            # Try to get table text too
            tables = page.extract_tables()
            table_text = ""
            for table in tables:
                for row in table:
                    if row:
                        table_text += "\t".join(str(c or "") for c in row) + "\n"

            combined = page_text + "\n" + table_text
            all_pages.append(combined)

            lower = combined.lower()
            if any(kw in lower for kw in _ALL_FIN_KEYWORDS):
                relevant_pages.append(combined)

    if relevant_pages:
        logger.debug("PDF: found %d relevant pages out of %d",
                     len(relevant_pages), len(all_pages))
        # Cap at 60 pages to stay within Groq context
        return "\n\n--- PAGE BREAK ---\n\n".join(relevant_pages[:60])

    # Fallback: send first 20 pages (sometimes TOC keywords differ)
    logger.warning("PDF: no financial keywords found, sending first 20 pages")
    return "\n\n--- PAGE BREAK ---\n\n".join(all_pages[:20])


# ── Excel helpers ─────────────────────────────────────────────────────────────

_EXCEL_FIN_SHEET_KEYWORDS = {
    "laba rugi", "income", "profit", "neraca", "balance",
    "arus kas", "cash flow", "posisi keuangan", "financial",
}


_EXCEL_ROW_KEYWORDS = (
    "revenue", "pendapatan", "laba", "rugi", "income", "profit", "loss",
    "aset", "asset", "liabilit", "ekuitas", "equity", "kas", "cash",
    "utang", "debt", "piutang", "receivable", "persediaan", "inventory",
    "operasi", "operating", "investasi", "investing", "ebitda", "eps",
    "beban", "expense", "bunga", "interest", "modal", "capital",
    "penjualan", "sales", "gross", "bersih", "net",
)

_MAX_ROWS_PER_SHEET = 120


def _extract_text_from_excel(content: bytes) -> str:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    text_parts: List[str] = []

    for sheet_name in wb.sheetnames:
        lower_name = sheet_name.lower()
        is_financial = any(kw in lower_name for kw in _EXCEL_FIN_SHEET_KEYWORDS)

        ws = wb[sheet_name]
        rows_text: List[str] = []
        row_count = 0

        for row in ws.iter_rows(values_only=True):
            if all(c is None for c in row):
                continue
            if row_count >= _MAX_ROWS_PER_SHEET:
                break

            row_str = "\t".join(str(c) if c is not None else "" for c in row)

            # Keep row if: sheet is financial, or row label matches keyword, or row has numbers
            first_cell = str(row[0] or "").lower()
            has_numbers = any(isinstance(c, (int, float)) for c in row)
            label_match = any(kw in first_cell for kw in _EXCEL_ROW_KEYWORDS)

            if is_financial or label_match or has_numbers:
                rows_text.append(row_str)
                row_count += 1

        if rows_text:
            text_parts.append(f"=== Sheet: {sheet_name} ===\n" + "\n".join(rows_text))

    return "\n\n".join(text_parts)


# ── LLM parsing ───────────────────────────────────────────────────────────────

async def _llm_parse(
    text: str,
    ticker: str,
    hint_year: Optional[int],
) -> List[FinancialYear]:
    # Groq free tier: 12,000 TPM. 20k chars ≈ 5k tokens, total stays under 8k.
    if len(text) > 20_000:
        text = text[:20_000] + "\n... [truncated]"

    year_hint = f"The document is likely for fiscal year {hint_year}." if hint_year else ""

    human_prompt = f"""Company ticker: {ticker}
{year_hint}

--- FINANCIAL DOCUMENT TEXT START ---
{text}
--- FINANCIAL DOCUMENT TEXT END ---

Extract all financial figures and return the JSON array as instructed."""

    llm = build_llm(max_tokens=4096)
    response = await llm.ainvoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=human_prompt),
    ])

    raw = response.content.strip()
    raw = _strip_markdown_fences(raw)

    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        parsed = [parsed]

    return [_coerce_financial_year(item) for item in parsed]


# ── Normalization helpers ─────────────────────────────────────────────────────

def _deduplicate_and_sort(years: List[FinancialYear]) -> List[FinancialYear]:
    """Merge duplicate years (later extraction wins) and sort ascending."""
    merged: Dict[int, FinancialYear] = {}
    for y in years:
        year_key = int(y["year"])
        if year_key not in merged:
            merged[year_key] = y
        else:
            # Merge: fill nulls from existing with new values
            merged[year_key] = _merge_year(merged[year_key], y)

    return sorted(merged.values(), key=lambda y: y["year"])


def _merge_year(base: FinancialYear, update: FinancialYear) -> FinancialYear:
    result = dict(base)
    for section in ("income_statement", "balance_sheet", "cash_flow"):
        merged_section = {**base.get(section, {})}  # type: ignore[operator]
        for k, v in update.get(section, {}).items():  # type: ignore[union-attr]
            if merged_section.get(k) is None and v is not None:
                merged_section[k] = v
        result[section] = merged_section
    return result  # type: ignore[return-value]


def _coerce_financial_year(raw: dict) -> FinancialYear:
    """Ensure all numeric fields are float or None."""
    def to_float(v: Any) -> Optional[float]:
        if v is None:
            return None
        try:
            return float(str(v).replace(",", "").replace(" ", ""))
        except (ValueError, TypeError):
            return None

    def coerce_section(d: dict) -> Dict[str, Optional[float]]:
        return {k: to_float(v) for k, v in d.items()}

    return FinancialYear(
        year=int(raw.get("year", 0)),
        income_statement=coerce_section(raw.get("income_statement", {})),
        balance_sheet=coerce_section(raw.get("balance_sheet", {})),
        cash_flow=coerce_section(raw.get("cash_flow", {})),
    )


def _strip_markdown_fences(text: str) -> str:
    text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```$", "", text, flags=re.MULTILINE)
    return text.strip()
