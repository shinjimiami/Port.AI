"""Unit tests for each LangGraph agent node (no real LLM calls)."""
import pytest

from app.agents.diversification_checker import diversification_checker_node
from app.agents.input_validator import input_validator_node
from app.schemas.portfolio import GeneratePortfolioRequest

# ── Helpers ────────────────────────────────────────────────────────────────────

def _base_state(**overrides):
    user_input = GeneratePortfolioRequest(
        budget=10_000,
        currency="USD",
        horizon="6 months",
        asset_classes=["US_STOCKS", "CRYPTO"],
    )
    state = {
        "user_input": user_input,
        "inferred_risk": None,
        "market_data": {},
        "allocation_plan": {},
        "selected_assets": [],
        "diversification_ok": False,
        "diversification_feedback": None,
        "retry_count": 0,
        "report": None,
        "errors": [],
    }
    state.update(overrides)
    return state


# ── INPUT_VALIDATOR ────────────────────────────────────────────────────────────

class TestInputValidator:
    def test_infers_moderate_risk_for_6_months(self):
        state = input_validator_node(_base_state())
        assert state["inferred_risk"] == "moderate"

    def test_infers_conservative_for_1_month(self):
        user_input = GeneratePortfolioRequest(
            budget=5_000, currency="USD",
            horizon="1 month", asset_classes=["US_STOCKS"],
        )
        state = input_validator_node(_base_state(user_input=user_input))
        assert state["inferred_risk"] == "conservative"

    def test_infers_aggressive_for_5_years(self):
        user_input = GeneratePortfolioRequest(
            budget=5_000, currency="USD",
            horizon="5 years", asset_classes=["US_STOCKS", "CRYPTO"],
        )
        state = input_validator_node(_base_state(user_input=user_input))
        assert state["inferred_risk"] == "aggressive"

    def test_respects_explicit_risk_tolerance(self):
        user_input = GeneratePortfolioRequest(
            budget=5_000, currency="USD",
            horizon="6 months", asset_classes=["US_STOCKS"],
            risk_tolerance="conservative",
        )
        state = input_validator_node(_base_state(user_input=user_input))
        assert state["inferred_risk"] == "conservative"

    def test_warns_about_crypto_with_conservative_profile(self):
        user_input = GeneratePortfolioRequest(
            budget=5_000, currency="USD",
            horizon="1 month",
            asset_classes=["US_STOCKS", "CRYPTO"],
        )
        state = input_validator_node(_base_state(user_input=user_input))
        assert any("conservative" in e.lower() for e in state["errors"])


# ── DIVERSIFICATION_CHECKER ───────────────────────────────────────────────────

class TestDiversificationChecker:
    def _make_assets(self, specs):
        """specs: list of (ticker, asset_class, sector, pct)"""
        return [
            {"ticker": t, "asset_class": ac, "sector": s, "allocation_percentage": p}
            for t, ac, s, p in specs
        ]

    def test_passes_clean_portfolio(self):
        assets = self._make_assets([
            ("AAPL",  "US_STOCKS", "Technology", 20),
            ("JPM",   "US_STOCKS", "Finance",    20),
            ("BBCA.JK", "IDX",     "Finance",    15),
            ("TLKM.JK", "IDX",     "Telecom",    15),
            ("BTC",   "CRYPTO",    "large_cap",  30),
        ])
        state = diversification_checker_node(_base_state(selected_assets=assets))
        assert state["diversification_ok"] is True
        assert state["diversification_feedback"] is None

    def test_fails_overweight_single_asset(self):
        assets = self._make_assets([
            ("AAPL", "US_STOCKS", "Technology", 40),   # > 25%
            ("MSFT", "US_STOCKS", "Technology", 30),
            ("BTC",  "CRYPTO",    "large_cap",  30),
        ])
        state = diversification_checker_node(_base_state(selected_assets=assets))
        assert state["diversification_ok"] is False
        assert "AAPL" in state["diversification_feedback"]

    def test_fails_sector_concentration(self):
        assets = self._make_assets([
            ("AAPL",  "US_STOCKS", "Technology", 20),
            ("MSFT",  "US_STOCKS", "Technology", 20),
            ("NVDA",  "US_STOCKS", "Technology", 20),   # 60% tech in US_STOCKS > 40%
            ("BTC",   "CRYPTO",    "large_cap",  20),
            ("ETH",   "CRYPTO",    "large_cap",  20),
        ])
        state = diversification_checker_node(_base_state(selected_assets=assets))
        assert state["diversification_ok"] is False
        assert "Technology" in state["diversification_feedback"]

    def test_increments_retry_count(self):
        assets = self._make_assets([
            ("AAPL", "US_STOCKS", "Technology", 30),  # > 25%
            ("BTC",  "CRYPTO",    "large_cap",  70),
        ])
        state = _base_state(selected_assets=assets, retry_count=0)
        new_state = diversification_checker_node(state)
        assert new_state["retry_count"] == 1

    def test_accepts_after_max_retries(self):
        assets = self._make_assets([
            ("AAPL", "US_STOCKS", "Technology", 30),
            ("BTC",  "CRYPTO",    "large_cap",  70),
        ])
        state = _base_state(selected_assets=assets, retry_count=3)  # at max
        new_state = diversification_checker_node(state)
        assert new_state["diversification_ok"] is True

    def test_correlation_heuristic_three_mega_tech(self):
        assets = self._make_assets([
            ("AAPL",  "US_STOCKS", "Technology", 10),
            ("MSFT",  "US_STOCKS", "Technology", 10),
            ("NVDA",  "US_STOCKS", "Technology", 10),   # 3 in mega_tech bucket
            ("GOOGL", "US_STOCKS", "Technology", 10),
            ("BTC",   "CRYPTO",    "large_cap",  60),
        ])
        state = diversification_checker_node(_base_state(selected_assets=assets))
        # Should be flagged for correlation
        assert state["diversification_ok"] is False
        assert "mega_tech" in state["diversification_feedback"].lower()
