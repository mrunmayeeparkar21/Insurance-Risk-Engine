# insurance_risk_engine/risk_metrics.py

import numpy as np
from phase2_python.insurance_risk_engine.inputs import PORTFOLIO


def compute_risk_metrics(
    losses: np.ndarray,
    params: dict = None,
) -> dict:
    """
    Compute all risk and capital adequacy metrics
    from simulated aggregate losses.
    """
    if params is None:
        params = PORTFOLIO

    gwp       = params["gross_written_premium"]
    exp_ratio = params["expense_ratio"]
    ri_ratio  = params["ri_cost_ratio"]
    avail_cap = params["available_capital"]
    mgmt_buf  = params["management_buffer"]

    expenses      = gwp * exp_ratio
    ri_cost       = gwp * ri_ratio
    net_available = gwp - expenses - ri_cost

    mean_loss = float(np.mean(losses))
    std_dev   = float(np.std(losses, ddof=1))

    var_95   = float(np.percentile(losses, 95.0))
    var_99   = float(np.percentile(losses, 99.0))
    var_99_5 = float(np.percentile(losses, 99.5))

    tail_95 = losses[losses > var_95]
    tail_99 = losses[losses > var_99]

    es_95 = float(np.mean(tail_95)) if len(tail_95) > 0 else var_95
    es_99 = float(np.mean(tail_99)) if len(tail_99) > 0 else var_99

    ruin_probability = float(np.mean(losses > (net_available + avail_cap)))
    net_profit       = gwp - mean_loss - expenses - ri_cost

    scr                    = max(var_99_5 - mean_loss, 0.0)
    management_buffer      = scr * mgmt_buf
    total_capital_required = scr + management_buffer

    if total_capital_required > 0:
        solvency_ratio = avail_cap / total_capital_required
    else:
        solvency_ratio = float("inf")

    if total_capital_required > 0:
        rorc = net_profit / total_capital_required
    else:
        rorc = float("inf")

    return {
        "mean_loss":              mean_loss,
        "std_dev":                std_dev,
        "var_95":                 var_95,
        "var_99":                 var_99,
        "var_99_5":               var_99_5,
        "es_95":                  es_95,
        "es_99":                  es_99,
        "ruin_probability":       ruin_probability,
        "net_available":          net_available,
        "scr":                    scr,
        "management_buffer":      management_buffer,
        "total_capital_required": total_capital_required,
        "solvency_ratio":         solvency_ratio,
        "net_profit":             net_profit,
        "rorc":                   rorc,
    }
