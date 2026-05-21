# insurance_risk_engine/deterministic_model.py

from phase2_python.insurance_risk_engine.inputs import PORTFOLIO


def run_deterministic_model(params: dict = None) -> dict:
    """
    Deterministic expected-value model.
    Replicates the Excel Calculations sheet exactly.
    """
    if params is None:
        params = PORTFOLIO

    gwp        = params["gross_written_premium"]
    n_policies = params["num_policies"]
    frequency  = params["claim_frequency"]
    mean_sev   = params["mean_severity"]
    exp_ratio  = params["expense_ratio"]
    ri_ratio   = params["ri_cost_ratio"]

    expected_claim_count = n_policies * frequency
    expected_gross_loss  = expected_claim_count * mean_sev
    expenses             = gwp * exp_ratio
    ri_cost              = gwp * ri_ratio
    net_profit           = gwp - expected_gross_loss - expenses - ri_cost

    loss_ratio     = expected_gross_loss / gwp
    combined_ratio = (expected_gross_loss + expenses + ri_cost) / gwp

    return {
        "gross_written_premium": gwp,
        "expected_claim_count":  expected_claim_count,
        "expected_gross_loss":   expected_gross_loss,
        "expenses":              expenses,
        "ri_cost":               ri_cost,
        "net_profit":            net_profit,
        "loss_ratio":            loss_ratio,
        "combined_ratio":        combined_ratio,
    }
