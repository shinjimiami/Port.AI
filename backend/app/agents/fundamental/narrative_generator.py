"""Node 7 — NARRATIVE_GENERATOR
ONE Groq LLM call. Generates full Bahasa Indonesia research report in Markdown.
"""
import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.fundamental.state import FundamentalState
from app.agents.llm import build_llm

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "**Disclaimer:** Laporan ini dibuat oleh sistem AI (PortAI) untuk tujuan "
    "edukasi dan simulasi semata. Bukan merupakan saran investasi, rekomendasi "
    "pembelian/penjualan efek, atau ajakan berinvestasi. Kinerja masa lalu tidak "
    "menjamin hasil di masa depan. Selalu konsultasikan keputusan investasi Anda "
    "dengan analis keuangan berlisensi."
)

SYSTEM_PROMPT = """Kamu adalah analis senior portofolio dari sekuritas Indonesia terkemuka.
Tugas kamu: tulis laporan riset fundamental yang profesional namun mudah dipahami investor ritel.

Gunakan Bahasa Indonesia yang baku dan informatif — seperti laporan riset dari BRI Danareksa,
Mirae Asset, atau Mandiri Sekuritas.

Laporan harus dalam format Markdown dengan section berikut (gunakan heading ##):

## 1. Gambaran Perusahaan
## 2. Kesehatan Keuangan
## 3. Analisis Pertumbuhan
## 4. Red Flag & Risiko
## 5. Valuasi
## 6. Entry Signal & Rekomendasi
## 7. Yang Perlu Dipantau

Tulis dengan angka spesifik dari data yang diberikan. Jangan generik.
Tone: profesional, faktual, langsung ke poin.
Panjang: 600–900 kata total.
JANGAN tambahkan disclaimer — sudah disertakan oleh sistem."""


async def narrative_generator_node(state: FundamentalState) -> FundamentalState:
    ticker        = state["ticker"]
    normalized    = state["normalized_data"]
    ratios_data   = state.get("ratios", {})
    trend         = state.get("trend_analysis", {})
    red_flags     = state.get("red_flags", [])
    valuation     = state.get("valuation", {})
    entry_signal  = state.get("entry_signal", {})
    current_price = state.get("current_price")
    errors        = list(state.get("errors", []))

    # Build a compact data summary for the LLM (avoid token overflow)
    summary = {
        "ticker":        ticker,
        "current_price": current_price,
        "years":         [y["year"] for y in sorted(normalized, key=lambda y: y["year"])],
        "latest_financials": normalized[-1] if normalized else {},
        "ratios_latest": ratios_data.get("latest_year", {}),
        "revenue_trend": trend.get("revenue", {}),
        "net_income_trend": trend.get("net_income", {}),
        "margin_trends": trend.get("margins", {}),
        "detected_patterns": trend.get("detected_patterns", []),
        "red_flags":     red_flags,
        "valuation":     {k: v for k, v in valuation.items() if k != "skipped"},
        "entry_signal":  entry_signal,
    }

    human_prompt = f"""Data analisis fundamental untuk saham **{ticker}**:

```json
{json.dumps(summary, indent=2, default=str)}
```

Tulis laporan riset sesuai instruksi. Gunakan angka dari data di atas.
Jika current_price tidak ada, skip section valuasi harga.
Laporan dalam Bahasa Indonesia."""

    try:
        llm = build_llm(max_tokens=4096)
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_prompt),
        ])
        narrative = response.content.strip()
    except Exception as exc:
        logger.error("NarrativeGenerator LLM failed: %s", exc)
        errors.append(f"Narrative generation failed: {exc}")
        narrative = _fallback_narrative(ticker, entry_signal)

    # Append disclaimer
    narrative = narrative + f"\n\n---\n\n{DISCLAIMER}"

    logger.info("NarrativeGenerator: report generated for %s", ticker)
    return {**state, "narrative_report": narrative, "errors": errors}


def _fallback_narrative(ticker: str, entry_signal: dict) -> str:
    score  = entry_signal.get("total_score", "N/A")
    signal = (entry_signal.get("signal") or {}).get("label", "N/A")
    return f"""## Laporan Fundamental — {ticker}

Analisis fundamental untuk **{ticker}** telah selesai diproses.

**Entry Signal:** {signal}
**Total Score:** {score}/100

Silakan lihat detail breakdown skor, rasio keuangan, dan red flag
pada panel analisis di bawah laporan ini."""
