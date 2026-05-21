# insurance_risk_engine/reinsurance.py

import numpy as np
from phase2_python.insurance_risk_engine.inputs import PORTFOLIO, SIMULATION
from phase2_python.insurance_risk_engine.stochastic_model import get_lognormal_params


def simulate_xl_reinsurance(params=None, sim_params=None, mle_params=None):
    """
    Stochastic XL Reinsurance Simulation

    Returns:
        dict containing:
        - gross & net losses
        - ruin probabilities
        - recovery data (for tables)
        - treaty parameters
    """

    if params is None:
        params = PORTFOLIO
    if sim_params is None:
        sim_params = SIMULATION


    # ─────────────────────────────────────────────
    # Treaty parameters
    # ─────────────────────────────────────────────
    XL_RETENTION = params["xl_retention"]
    XL_LIMIT = params["xl_limit"]
    N_SIMS = sim_params["num_sims"]

    # ─────────────────────────────────────────────
    # Frequency & severity setup
    # ─────────────────────────────────────────────
    lambda_ = params["num_policies"] * params["claim_frequency"]

    if mle_params is not None:
        mu = mle_params["mu"]
        sigma = mle_params["sigma"]
    else:
        mu, sigma = get_lognormal_params(
            params["mean_severity"],
            params["severity_cv"]
        )

    seed = sim_params.get("random_seed_reinsurance", 99)
    rng = np.random.default_rng(seed)

    # ─────────────────────────────────────────────
    # Simulate claims
    # ─────────────────────────────────────────────
    claim_counts = rng.poisson(lambda_, size=N_SIMS)
    total_claims = int(claim_counts.sum())

    severities = rng.lognormal(mu, sigma, total_claims)

    # Map claims to simulations
    idx = np.repeat(np.arange(N_SIMS), claim_counts)

    # ─────────────────────────────────────────────
    # Gross losses
    # ─────────────────────────────────────────────
    losses_gross = np.bincount(
        idx,
        weights=severities,
        minlength=N_SIMS
    )

    # ─────────────────────────────────────────────
    # XL Reinsurance Recovery
    # ─────────────────────────────────────────────
    recovery = np.maximum(
        0,
        np.minimum(severities - XL_RETENTION, XL_LIMIT)
    )

    # Net losses
    net_sev = severities - recovery

    losses_net = np.bincount(
        idx,
        weights=net_sev,
        minlength=N_SIMS
    )

    # ─────────────────────────────────────────────
    # Recovery statistics (for tables)
    # ─────────────────────────────────────────────
    annual_recovery = np.bincount(
        idx,
        weights=recovery,
        minlength=N_SIMS
    )

    # ─────────────────────────────────────────────
    # Ruin calculation
    # ─────────────────────────────────────────────
    net_funds = (
        params["gross_written_premium"]
        * (1 - params["expense_ratio"] - params["ri_cost_ratio"])
        + params["available_capital"]
    )

    ruin_gross = np.mean(losses_gross > net_funds)
    ruin_net = np.mean(losses_net > net_funds)

    # ─────────────────────────────────────────────
    # Return everything needed for notebook display
    # ─────────────────────────────────────────────
    return {
        "losses_gross": losses_gross,
        "losses_net": losses_net,
        "ruin_gross": ruin_gross,
        "ruin_net": ruin_net,
        "recovery": recovery,
        "annual_recovery": annual_recovery,
        "XL_RETENTION": XL_RETENTION,
        "XL_LIMIT": XL_LIMIT,
    }
