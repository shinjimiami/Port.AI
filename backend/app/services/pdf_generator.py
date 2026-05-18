"""
Generate a professional PDF report for a completed portfolio.
Uses fpdf2 (pure Python, no system dependencies).
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict

from fpdf import FPDF, XPos, YPos

# ── Palette ───────────────────────────────────────────────────────────────────
BRAND_R, BRAND_G, BRAND_B = 37, 99, 235      # blue-600
DARK_R,  DARK_G,  DARK_B  = 17, 24,  39      # gray-900
MID_R,   MID_G,   MID_B   = 107, 114, 128    # gray-500
LIGHT_R, LIGHT_G, LIGHT_B = 249, 250, 251    # gray-50
WARN_R,  WARN_G,  WARN_B  = 217, 119, 6      # amber-600

ASSET_CLASS_COLORS: Dict[str, tuple] = {
    "US_STOCKS": (59, 130, 246),   # blue-500
    "IDX":       (16, 185, 129),   # emerald-500
    "CRYPTO":    (139, 92, 246),   # violet-500
}

RISK_COLORS: Dict[str, tuple] = {
    "conservative": (22,  163, 74),   # green-600
    "moderate":     (217, 119, 6),    # amber-600
    "aggressive":   (220, 38,  38),   # red-600
    "Low":          (22,  163, 74),
    "Moderate":     (217, 119, 6),
    "High":         (220, 38,  38),
}


class PortAIPDF(FPDF):
    def __init__(self, report: Dict[str, Any]):
        super().__init__()
        self.report = report
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(auto=True, margin=20)
        self.add_page()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _rgb(self, r: int, g: int, b: int):
        self.set_text_color(r, g, b)

    def _fill(self, r: int, g: int, b: int):
        self.set_fill_color(r, g, b)

    def _draw(self, r: int, g: int, b: int):
        self.set_draw_color(r, g, b)

    def _section_title(self, title: str):
        self.ln(4)
        self._rgb(BRAND_R, BRAND_G, BRAND_B)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, title.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._draw(BRAND_R, BRAND_G, BRAND_B)
        self.set_line_width(0.5)
        self.line(self.get_x(), self.get_y(), self.get_x() + 174, self.get_y())
        self.ln(3)

    def _body_text(self, text: str, color=(DARK_R, DARK_G, DARK_B)):
        self._rgb(*color)
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def _kv_row(self, label: str, value: str, bold_value=False):
        self._rgb(MID_R, MID_G, MID_B)
        self.set_font("Helvetica", "", 9)
        self.cell(55, 6, label)
        self._rgb(DARK_R, DARK_G, DARK_B)
        self.set_font("Helvetica", "B" if bold_value else "", 9)
        self.cell(0, 6, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        r = self.report

        # Brand bar
        self._fill(BRAND_R, BRAND_G, BRAND_B)
        self.rect(0, 0, 210, 22, "F")
        self.set_y(5)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 12, "PortAI — Portfolio Report", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Sub-header meta
        self.set_y(26)
        self._fill(LIGHT_R, LIGHT_G, LIGHT_B)
        self.rect(0, 26, 210, 18, "F")
        self.set_y(29)

        generated_at = datetime.utcnow().strftime("%B %d, %Y")
        risk = r.get("risk_profile", "—")
        rc = RISK_COLORS.get(risk, (DARK_R, DARK_G, DARK_B))

        self.set_font("Helvetica", "", 9)
        self._rgb(MID_R, MID_G, MID_B)
        budget_str = f"{r.get('currency', 'USD')} {r.get('total_budget', 0):,.0f}"
        meta = (
            f"Budget: {budget_str}   ·   "
            f"Horizon: {r.get('horizon', '—')}   ·   "
            f"Generated: {generated_at}"
        )
        self.cell(0, 5, meta, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)
        self._rgb(*rc)
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 5, f"Risk Profile: {risk.capitalize()}", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(6)

    # ── Summary ───────────────────────────────────────────────────────────────

    def _build_summary(self):
        self._section_title("Executive Summary")
        self._body_text(self.report.get("summary", ""))

    # ── Allocation table ──────────────────────────────────────────────────────

    def _build_allocation(self):
        self._section_title("Asset Allocation")
        r = self.report
        currency = r.get("currency", "USD")
        allocation = r.get("allocation", [])

        # Table header
        self._fill(BRAND_R, BRAND_G, BRAND_B)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(255, 255, 255)
        col_w = [80, 40, 54]
        self.cell(col_w[0], 7, "Asset Class", fill=True)
        self.cell(col_w[1], 7, "Allocation %", fill=True, align="C")
        self.cell(col_w[2], 7, f"Amount ({currency})", fill=True, align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        for i, item in enumerate(allocation):
            ac = item.get("asset_class", "")
            pct = item.get("percentage", 0)
            amt = item.get("amount", 0)
            color = ASSET_CLASS_COLORS.get(ac, (DARK_R, DARK_G, DARK_B))

            fill_bg = (i % 2 == 0)
            if fill_bg:
                self._fill(249, 250, 251)
            self.set_font("Helvetica", "B", 9)
            self._rgb(*color)
            self.cell(col_w[0], 6, ac.replace("_", " "), fill=fill_bg)
            self._rgb(DARK_R, DARK_G, DARK_B)
            self.set_font("Helvetica", "", 9)
            self.cell(col_w[1], 6, f"{pct:.1f}%", fill=fill_bg, align="C")
            self.cell(col_w[2], 6, f"{amt:,.2f}", fill=fill_bg, align="R",
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.ln(3)

    # ── Assets table ──────────────────────────────────────────────────────────

    def _build_assets(self):
        self._section_title("Selected Assets")
        r = self.report
        currency = r.get("currency", "USD")
        assets = r.get("assets", [])

        # Header
        self._fill(BRAND_R, BRAND_G, BRAND_B)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(255, 255, 255)
        cols = [22, 52, 28, 24, 24, 24]
        headers = ["Ticker", "Name", "Class", "Alloc%", f"Amt({currency})", "Return"]
        for w, h in zip(cols, headers):
            self.cell(w, 6, h, fill=True, align="C")
        self.ln()

        for i, asset in enumerate(assets):
            ac = asset.get("asset_class", "")
            fill_bg = (i % 2 == 0)
            if fill_bg:
                self._fill(249, 250, 251)

            color = ASSET_CLASS_COLORS.get(ac, (DARK_R, DARK_G, DARK_B))
            self.set_font("Helvetica", "B", 8)
            self._rgb(*color)
            self.cell(cols[0], 5.5, str(asset.get("ticker", ""))[:8], fill=fill_bg, align="C")

            self._rgb(DARK_R, DARK_G, DARK_B)
            self.set_font("Helvetica", "", 8)
            name = str(asset.get("name", ""))[:22]
            self.cell(cols[1], 5.5, name, fill=fill_bg)
            self.cell(cols[2], 5.5, ac.replace("_", "")[:8], fill=fill_bg, align="C")
            self.cell(cols[3], 5.5, f"{asset.get('allocation_percentage', 0):.1f}%",
                      fill=fill_bg, align="C")
            self.cell(cols[4], 5.5, f"{asset.get('amount', 0):,.0f}",
                      fill=fill_bg, align="R")
            exp_ret = str(asset.get("expected_return") or "—")[:8]
            self.cell(cols[5], 5.5, exp_ret, fill=fill_bg, align="C",
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Per-asset reasoning
        self.ln(4)
        self.set_font("Helvetica", "B", 9)
        self._rgb(DARK_R, DARK_G, DARK_B)
        self.cell(0, 5, "Asset Rationale", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)
        for asset in assets:
            ticker = asset.get("ticker", "")
            reasoning = asset.get("reasoning", "")
            if not reasoning:
                continue
            color = ASSET_CLASS_COLORS.get(asset.get("asset_class", ""), (MID_R, MID_G, MID_B))
            self._rgb(*color)
            self.set_font("Helvetica", "B", 8)
            self.cell(22, 5, ticker)
            self._rgb(DARK_R, DARK_G, DARK_B)
            self.set_font("Helvetica", "", 8)
            # Truncate to avoid overflow
            self.multi_cell(0, 4.5, reasoning[:300], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1)

    # ── Risk metrics ──────────────────────────────────────────────────────────

    def _build_risk(self):
        self._section_title("Risk & Return Metrics")
        rm = self.report.get("risk_metrics", {})
        reb = self.report.get("rebalancing", {})

        self._kv_row("Expected Return", rm.get("expected_return", "—"), bold_value=True)
        risk_level = rm.get("risk_level", "—")
        rc = RISK_COLORS.get(risk_level, (DARK_R, DARK_G, DARK_B))
        self._rgb(MID_R, MID_G, MID_B)
        self.set_font("Helvetica", "", 9)
        self.cell(55, 6, "Risk Level")
        self._rgb(*rc)
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 6, risk_level, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._kv_row("Max Drawdown Est.", rm.get("max_drawdown_estimate", "—"))
        self._kv_row("Sharpe Estimate",   rm.get("sharpe_estimate", "—"))

        if reb.get("suggested_date"):
            self.ln(2)
            self._kv_row("Rebalancing Date", reb["suggested_date"], bold_value=True)
        triggers = reb.get("trigger_conditions", [])
        if triggers:
            self.ln(1)
            self._rgb(MID_R, MID_G, MID_B)
            self.set_font("Helvetica", "", 8)
            self.cell(0, 5, "Review triggers:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            for t in triggers:
                self._rgb(DARK_R, DARK_G, DARK_B)
                self.multi_cell(0, 4.5, f"  → {t}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Market context ────────────────────────────────────────────────────────

    def _build_market_context(self):
        ctx = self.report.get("market_context", "")
        if not ctx:
            return
        self._section_title("Market Context")
        self._body_text(ctx, color=(MID_R, MID_G, MID_B))

    # ── Warnings ──────────────────────────────────────────────────────────────

    def _build_warnings(self):
        warnings = self.report.get("warnings", [])
        if not warnings:
            return
        self._section_title("Warnings")
        for w in warnings:
            self._rgb(WARN_R, WARN_G, WARN_B)
            self.set_font("Helvetica", "", 9)
            self.multi_cell(0, 5, f"⚠  {w}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1)

    # ── Disclaimer ────────────────────────────────────────────────────────────

    def _build_disclaimer(self):
        disclaimer = self.report.get("disclaimer", "")
        if not disclaimer:
            return
        self.ln(4)
        self._fill(249, 250, 251)
        self.set_font("Helvetica", "I", 7.5)
        self._rgb(MID_R, MID_G, MID_B)
        self.multi_cell(0, 4, disclaimer, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Footer ────────────────────────────────────────────────────────────────

    def footer(self):
        self.set_y(-14)
        self._draw(200, 200, 200)
        self.set_line_width(0.3)
        self.line(18, self.get_y(), 192, self.get_y())
        self.set_font("Helvetica", "", 7)
        self._rgb(MID_R, MID_G, MID_B)
        self.cell(0, 8, f"PortAI — Educational AI Portfolio Advisor  ·  Page {self.page_no()}",
                  align="C")

    # ── Build all ─────────────────────────────────────────────────────────────

    def build(self) -> bytes:
        self._build_header()
        self._build_summary()
        self._build_allocation()
        self._build_assets()
        self._build_risk()
        self._build_market_context()
        self._build_warnings()
        self._build_disclaimer()
        return bytes(self.output())


def generate_portfolio_pdf(report: Dict[str, Any]) -> bytes:
    """Return the PDF bytes for a completed portfolio report."""
    pdf = PortAIPDF(report)
    return pdf.build()
