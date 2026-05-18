"""Node 1 — INPUT_VALIDATOR: normalises user input and infers risk profile."""
import logging

from app.agents.state import PortfolioState

logger = logging.getLogger(__name__)

# Horizon → risk bias mapping (used when user doesn't specify)
HORIZON_TO_RISK = {
    "1 month":  "conservative",
    "3 months": "conservative",
    "6 months": "moderate",
    "1 year":   "moderate",
    "3 years":  "moderate",
    "5 years":  "aggressive",
}

# Crypto allocation ceiling per risk profile
CRYPTO_MAX_BY_RISK = {
    "conservative": 10,
    "moderate": 30,
    "aggressive": 50,
}


def input_validator_node(state: PortfolioState) -> PortfolioState:
    """
    Validate and normalise user input.
    Infer risk profile from horizon when the user omits it.
    """
    user_input = state["user_input"]
    errors: list[str] = list(state.get("errors", []))

    # Validate budget
    if user_input.budget <= 0:
        errors.append("Budget must be greater than zero.")

    # Infer risk if not provided
    inferred = user_input.risk_tolerance
    if not inferred:
        inferred = HORIZON_TO_RISK.get(user_input.horizon, "moderate")
        logger.info("Risk not specified — inferred '%s' from horizon '%s'", inferred, user_input.horizon)

    # Warn if crypto is requested with a conservative profile
    if "CRYPTO" in user_input.asset_classes and inferred == "conservative":
        errors.append(
            "Warning: Crypto assets are high-risk. "
            "For a conservative profile the crypto allocation will be capped at 10%."
        )

    logger.info(
        "InputValidator: budget=%.2f %s, horizon=%s, risk=%s, classes=%s",
        user_input.budget,
        user_input.currency,
        user_input.horizon,
        inferred,
        user_input.asset_classes,
    )

    return {
        **state,
        "inferred_risk": inferred,
        "errors": errors,
    }
