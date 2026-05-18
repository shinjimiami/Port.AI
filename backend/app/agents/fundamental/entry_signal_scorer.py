"""Node 6 — ENTRY_SIGNAL_SCORER
Pure Python. No LLM.
Aggregates all node outputs into a 100-pt score and entry signal.
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.fundamental.state import FundamentalState

logger = logging.getLogger(__name__)

SIGNALS = [
    (85, "STRONG_BUY",  "🟢⚡ STRONG BUY"),
    (70, "BUY",         "🟢 BUY"),
    (55, "MODERATE_BUY","🟡 MODERATE BUY / WATCH"),
    (40, "NEUTRAL",     "🟠 NEUTRAL / HOLD"),
    (0,  "AVOID",       "🔴 AVOID"),
]

ZONE_VALUATION_SCORES = {
    "DEEPLY_UNDERVALUED":       15,
    "UNDERVALUED":              12,
    "FAIRLY_VALUED":             8,
    "OVERVALUED":                4,
    "SIGNIFICANTLY_OVERVALUED":  0,
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _signal_label(score: float) -> Dict[str, str]:
    for threshold, key, label in SIGNALS:
        if score >= threshold:
            return {"key": key, "label": label}
    return {"key": "AVOID", "label": "🔴 AVOID"}


async def entry_signal_scorer_node(state: FundamentalState) -> FundamentalState:
    ratios_data:    Dict[str, Any] = state.get("ratios", {})
    trend:          Dict[str, Any] = state.get("trend_analysis", {})
    red_flags:      List[dict]     = state.get("red_flags", [])
    valuation:      Dict[str, Any] = state.get("valuation", {})
    normalized                     = state["normalized_data"]
    errors = list(state.get("errors", []))

    ratios_years: List[dict] = ratios_data.get("years", [])
    latest_ratios: dict      = ratios_data.get("latest_year", {})

    # ── 1. Fundamental Health (25 pts) ────────────────────────────────────
    health_score = 0.0

    roe = latest_ratios.get("profitability", {}).get("roe_pct")
    if roe is not None:
        health_score += _clamp(roe / 20 * 8, 0, 8)   # 8 pts max (20% ROE = full)

    current_ratio = latest_ratios.get("liquidity", {}).get("current_ratio")
    if current_ratio is not None:
        health_score += _clamp((current_ratio - 1) / 1 * 7, 0, 7)  # 7 pts (CR≥2 = full)

    der = latest_ratios.get("solvency", {}).get("der")
    if der is not None:
        health_score += _clamp((3 - der) / 3 * 10, 0, 10)  # 10 pts (DER=0 = full)

    health_score = _clamp(health_score, 0, 25)

    # ── 2. Growth Quality (30 pts) ────────────────────────────────────────
    growth_score = 0.0

    rev_trend = trend.get("revenue", {}).get("trend")
    if rev_trend == "ACCELERATING":
        growth_score += 12
    elif rev_trend == "STABLE":
        growth_score += 9
    elif rev_trend == "DECELERATING":
        growth_score += 4

    ni_trend = trend.get("net_income", {}).get("trend")
    if ni_trend == "ACCELERATING":
        growth_score += 10
    elif ni_trend == "STABLE":
        growth_score += 7
    elif ni_trend == "DECELERATING":
        growth_score += 3

    fcf_trend = trend.get("free_cash_flow", {}).get("trend")
    if fcf_trend == "ACCELERATING":
        growth_score += 8
    elif fcf_trend == "STABLE":
        growth_score += 6
    elif fcf_trend == "DECELERATING":
        growth_score += 2

    growth_score = _clamp(growth_score, 0, 30)

    # ── 3. Earnings Integrity (20 pts) ────────────────────────────────────
    integrity_score = 20.0

    high_flags   = sum(1 for f in red_flags if f.get("severity") == "HIGH")
    medium_flags = sum(1 for f in red_flags if f.get("severity") == "MEDIUM")

    integrity_score -= high_flags   * 5
    integrity_score -= medium_flags * 2
    integrity_score = _clamp(integrity_score, 0, 20)

    # ── 4. Valuation (15 pts) ─────────────────────────────────────────────
    valuation_score = 0.0
    if not valuation.get("skipped"):
        zone = valuation.get("zone", {})
        zone_key = zone.get("key") if zone else None
        valuation_score = ZONE_VALUATION_SCORES.get(zone_key or "", 0)
    else:
        # No price → give neutral 7.5/15 so it doesn't penalise
        valuation_score = 7.5

    # ── 5. Business Momentum (10 pts) ────────────────────────────────────
    momentum_score = 0.0
    if len(ratios_years) >= 2:
        latest_nm = (ratios_years[-1].get("profitability") or {}).get("net_margin_pct")
        prev_nm   = (ratios_years[-2].get("profitability") or {}).get("net_margin_pct")
        if latest_nm is not None and prev_nm is not None:
            if latest_nm > prev_nm:
                momentum_score += 5
        latest_roe = (ratios_years[-1].get("profitability") or {}).get("roe_pct")
        prev_roe   = (ratios_years[-2].get("profitability") or {}).get("roe_pct")
        if latest_roe is not None and prev_roe is not None:
            if latest_roe > prev_roe:
                momentum_score += 5

    momentum_score = _clamp(momentum_score, 0, 10)

    # ── Total ─────────────────────────────────────────────────────────────
    total = health_score + growth_score + integrity_score + valuation_score + momentum_score
    total = round(_clamp(total, 0, 100), 1)

    signal = _signal_label(total)

    # ── Key strengths & risks ──────────────────────────────────────────────
    strengths: List[str] = []
    risks:     List[str] = []

    if roe and roe > 15:
        strengths.append(f"ROE tinggi {roe:.1f}% — efisiensi penggunaan modal pemegang saham baik.")
    if rev_trend in ("ACCELERATING", "STABLE"):
        cagr = trend.get("revenue", {}).get("cagr_pct")
        if cagr:
            strengths.append(f"Pendapatan tumbuh konsisten, CAGR {cagr:.1f}%.")
    if fcf_trend in ("ACCELERATING", "STABLE"):
        strengths.append("Free Cash Flow positif dan tumbuh — kualitas laba solid.")
    if current_ratio and current_ratio > 2:
        strengths.append(f"Likuiditas kuat, Current Ratio {current_ratio:.2f}x.")
    if not red_flags:
        strengths.append("Tidak ditemukan red flag material dalam laporan keuangan.")

    for flag in red_flags[:3]:
        risks.append(flag["description"])

    if der and der > 1.5:
        risks.append(f"Leverage cukup tinggi (DER {der:.2f}x) — perhatikan beban bunga.")
    if trend.get("margins", {}).get("net_trend") == "COMPRESSING":
        risks.append("Net margin menunjukkan tren menyempit dalam 3 tahun terakhir.")

    # ── Entry zone suggestion ─────────────────────────────────────────────
    entry_zone: Optional[Dict[str, float]] = None
    if not valuation.get("skipped"):
        intrinsic = (valuation.get("dcf") or {}).get("intrinsic_value_per_share")
        price     = state.get("current_price")
        if intrinsic and price:
            entry_zone = {
                "attractive_entry":  round(intrinsic * 0.85, 2),
                "fair_entry":        round(intrinsic * 0.95, 2),
                "current_price":     price,
                "intrinsic_estimate": round(intrinsic, 2),
            }

    entry_signal = {
        "total_score": total,
        "signal":      signal,
        "breakdown": {
            "fundamental_health":  round(health_score, 1),
            "growth_quality":      round(growth_score, 1),
            "earnings_integrity":  round(integrity_score, 1),
            "valuation":           round(valuation_score, 1),
            "business_momentum":   round(momentum_score, 1),
        },
        "key_strengths": strengths[:3],
        "key_risks":     risks[:3],
        "entry_zone":    entry_zone,
        "suggested_horizon": _suggest_horizon(total, trend),
    }

    logger.info("EntrySignalScorer: score=%.1f → %s", total, signal["key"])
    return {**state, "entry_signal": entry_signal, "errors": errors}


def _suggest_horizon(score: float, trend: Dict[str, Any]) -> str:
    rev_trend = trend.get("revenue", {}).get("trend", "")
    if score >= 70 and rev_trend in ("ACCELERATING", "STABLE"):
        return "Menengah–Panjang (1–3 tahun)"
    if score >= 55:
        return "Menengah (6–12 bulan)"
    return "Spekulatif — evaluasi ulang setiap kuartal"
