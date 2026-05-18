"""
Node 5 — DIVERSIFICATION_CHECKER

Validates three rules and adds a correlation heuristic:
  1. No single asset > 25% of total portfolio.
  2. No single sector > 40% of its asset class.
  3. Total allocation sum ≈ 100%.
  4. Correlation heuristic: penalise pairs from the same sub-category
     (e.g. two large-cap cryptos, two US tech stocks).
"""
import logging
from collections import defaultdict
from typing import List

from app.agents.state import PortfolioState

logger = logging.getLogger(__name__)

MAX_ASSET_PCT = 25.0
MAX_SECTOR_PCT = 40.0
MAX_RETRIES = 3

# Known high-correlation groups (same asset class + same sub-bucket)
# If a portfolio holds ≥ 3 assets from the same bucket it gets a warning.
CORRELATION_BUCKETS = {
    "US_STOCKS": {
        "mega_tech": {"AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN"},
        "us_banks":  {"JPM", "BAC", "WFC", "GS", "MS", "C"},
        "ev":        {"TSLA", "RIVN", "LCID", "NIO"},
    },
    "IDX": {
        "state_banks": {"BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK"},
        "idx_telco":   {"TLKM.JK", "EXCL.JK", "ISAT.JK"},
    },
    "CRYPTO": {
        "large_cap":  {"bitcoin", "BTC", "ethereum", "ETH", "binancecoin", "BNB"},
        "l1_chains":  {"solana", "SOL", "cardano", "ADA", "avalanche-2", "AVAX", "polkadot", "DOT"},
        "defi_tokens": {"uniswap", "UNI", "aave", "AAVE", "maker", "MKR", "compound", "COMP"},
    },
}


def _check_correlation(assets: List[dict]) -> List[str]:
    """
    Return feedback strings for highly correlated asset groupings.
    Uses a heuristic: ≥ 3 assets from the same correlation bucket.
    """
    feedback: List[str] = []

    for asset_class, buckets in CORRELATION_BUCKETS.items():
        class_assets = [
            a for a in assets
            if a.get("asset_class", "").upper() == asset_class
        ]
        if not class_assets:
            continue

        tickers_in_class = {
            (a.get("ticker") or a.get("symbol") or "").upper()
            for a in class_assets
        }

        for bucket_name, bucket_members in buckets.items():
            upper_members = {m.upper() for m in bucket_members}
            overlap = tickers_in_class & upper_members
            if len(overlap) >= 3:
                feedback.append(
                    f"{asset_class}: {len(overlap)} assets from the highly correlated "
                    f"'{bucket_name}' group ({', '.join(sorted(overlap))}). "
                    f"Consider replacing 1-2 with assets from a different bucket."
                )

    return feedback


def diversification_checker_node(state: PortfolioState) -> PortfolioState:
    assets: List[dict] = state.get("selected_assets", [])
    feedback_parts: List[str] = []

    # ── Rule 1: single-asset cap ───────────────────────────────────────────
    for asset in assets:
        pct = float(asset.get("allocation_percentage", 0))
        if pct > MAX_ASSET_PCT:
            feedback_parts.append(
                f"{asset.get('ticker')} is {pct:.1f}% of total portfolio — "
                f"max allowed is {MAX_ASSET_PCT}%."
            )

    # ── Rule 2: sector concentration within each asset class ───────────────
    class_sector: dict = defaultdict(lambda: defaultdict(float))
    class_total: dict = defaultdict(float)
    for asset in assets:
        ac = asset.get("asset_class", "UNKNOWN")
        sector = asset.get("sector", "Unknown")
        pct = float(asset.get("allocation_percentage", 0))
        class_sector[ac][sector] += pct
        class_total[ac] += pct

    for ac, sectors in class_sector.items():
        ac_total = class_total[ac] or 1
        for sector, sector_pct in sectors.items():
            sector_share = (sector_pct / ac_total) * 100
            if sector_share > MAX_SECTOR_PCT:
                feedback_parts.append(
                    f"{ac} – {sector} sector is {sector_share:.1f}% of {ac} "
                    f"allocation (max {MAX_SECTOR_PCT}%)."
                )

    # ── Rule 3: total allocation sanity ───────────────────────────────────
    total_pct = sum(float(a.get("allocation_percentage", 0)) for a in assets)
    if abs(total_pct - 100) > 5:
        feedback_parts.append(
            f"Total allocation is {total_pct:.1f}% — should be close to 100%."
        )

    # ── Rule 4: correlation heuristic ─────────────────────────────────────
    corr_feedback = _check_correlation(assets)
    feedback_parts.extend(corr_feedback)

    retry_count = state.get("retry_count", 0)
    diversification_ok = len(feedback_parts) == 0

    if not diversification_ok:
        if retry_count >= MAX_RETRIES:
            logger.warning(
                "DiversificationChecker: violations remain after %d retries — accepting: %s",
                MAX_RETRIES, feedback_parts,
            )
            return {
                **state,
                "diversification_ok": True,
                "diversification_feedback": None,
                "errors": state.get("errors", []) + [
                    f"Portfolio accepted with minor diversification issues "
                    f"after {MAX_RETRIES} retries: {'; '.join(feedback_parts)}"
                ],
            }

        logger.info(
            "DiversificationChecker: %d violation(s) (attempt %d/%d): %s",
            len(feedback_parts), retry_count + 1, MAX_RETRIES, feedback_parts,
        )
        return {
            **state,
            "diversification_ok": False,
            "diversification_feedback": " | ".join(feedback_parts),
            "retry_count": retry_count + 1,
        }

    logger.info("DiversificationChecker: all rules pass")
    return {
        **state,
        "diversification_ok": True,
        "diversification_feedback": None,
    }
