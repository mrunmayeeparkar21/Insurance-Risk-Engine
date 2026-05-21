# insurance_risk_engine/optimization.py

from scipy.optimize import brentq
from phase2_python.insurance_risk_engine.stochastic_model import run_monte_carlo
from phase2_python.insurance_risk_engine.risk_metrics import compute_risk_metrics
from phase2_python.insurance_risk_engine.inputs import PORTFOLIO, SIMULATION


def _deterministic_profit(premium: float, base_params: dict) -> float:
    exp_ratio  = base_params["expense_ratio"]
    ri_ratio   = base_params["ri_cost_ratio"]
    n_policies = base_params["num_policies"]
    freq       = base_params["claim_frequency"]
    mean_sev   = base_params["mean_severity"]

    expected_loss = n_policies * freq * mean_sev
    expenses      = premium * exp_ratio
    ri_cost       = premium * ri_ratio

    return premium - expected_loss - expenses - ri_cost


def _stochastic_ruin_probability(
    premium: float,
    base_params: dict,
) -> float:
    test_params = {**base_params, "gross_written_premium": premium}
    losses, _   = run_monte_carlo(params=test_params, sim_params=SIMULATION)
    metrics     = compute_risk_metrics(losses, params=test_params)
    return metrics["ruin_probability"]


def _combined_ratio_at_premium(
    premium: float,
    base_params: dict,
) -> float:
    exp_ratio  = base_params["expense_ratio"]
    ri_ratio   = base_params["ri_cost_ratio"]
    n_policies = base_params["num_policies"]
    freq       = base_params["claim_frequency"]
    mean_sev   = base_params["mean_severity"]

    expected_loss = n_policies * freq * mean_sev
    expenses      = premium * exp_ratio
    ri_cost       = premium * ri_ratio

    return (expected_loss + expenses + ri_cost) / premium


def premium_for_breakeven(base_params: dict = None) -> float:
    if base_params is None:
        base_params = PORTFOLIO

    current = base_params["gross_written_premium"]
    lo, hi  = current * 0.5, current * 2.0

    result = brentq(
        f=lambda p: _deterministic_profit(p, base_params),
        a=lo, b=hi,
        xtol=1_000, rtol=1e-6, maxiter=100,
    )
    return float(result)


def premium_for_target_ruin(
    target_ruin: float = 0.05,
    base_params: dict = None,
) -> float:
    if base_params is None:
        base_params = PORTFOLIO

    current = base_params["gross_written_premium"]
    lo, hi  = current * 0.5, current * 2.0

    def objective(premium: float) -> float:
        return _stochastic_ruin_probability(premium, base_params) - target_ruin
        
    # If current premium already satisfies target ruin, no increase needed
    if objective(base_params["gross_written_premium"]) <= 0:
        return base_params["gross_written_premium"]
        
    result = brentq(
        f=objective,
        a=lo, b=hi,
        xtol=1_000, rtol=1e-4, maxiter=50,
    )
    return float(result)


def premium_for_target_combined_ratio(
    target_cr: float = 1.0,
    base_params: dict = None,
) -> float:
    if base_params is None:
        base_params = PORTFOLIO

    current = base_params["gross_written_premium"]
    lo, hi  = current * 0.5, current * 2.0

    def objective(premium: float) -> float:
        return _combined_ratio_at_premium(premium, base_params) - target_cr

    result = brentq(
        f=objective,
        a=lo, b=hi,
        xtol=1_000, rtol=1e-6, maxiter=100,
    )
    return float(result)