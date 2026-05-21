# insurance_risk_engine/stochastic_model.py

import numpy as np
from phase2_python.insurance_risk_engine.inputs import PORTFOLIO, SIMULATION


def get_lognormal_params(mean: float, cv: float) -> tuple:
    """
    Convert arithmetic mean and CV to lognormal (mu, sigma).
    """
    sigma_sq = np.log(1.0 + cv ** 2)
    sigma    = np.sqrt(sigma_sq)
    mu       = np.log(mean) - sigma_sq / 2.0
    return mu, sigma


def run_monte_carlo(
    params: dict = None,
    sim_params: dict = None,
    apply_reinsurance: bool = False
) -> tuple:
    """
    Collective Risk Model Monte Carlo simulation.
    N ~ Poisson(lambda), Xi ~ Lognormal(mu, sigma)
    Returns (total_losses, claim_counts)
    """
    if params is None:
        params = PORTFOLIO
    if sim_params is None:
        sim_params = SIMULATION

    num_sims   = sim_params["num_sims"]
    seed       = sim_params.get("random_seed_mc", 42)
    n_policies = params["num_policies"]
    freq       = params["claim_frequency"]
    lam = float(n_policies) * freq
    
    # MLE-fitted lognormal parameters when available
    if "mu" in params and "sigma" in params:
        mu = params["mu"]
        sigma = params["sigma"]
    else:
        mean_sev = params["mean_severity"]
        cv = params["severity_cv"]
        mu, sigma = get_lognormal_params(mean_sev, cv)

    rng = np.random.default_rng(seed)

    claim_counts = rng.poisson(lam=lam, size=num_sims)

    total_claims = claim_counts.sum()
    claim_counts = claim_counts.astype(int)
    if total_claims == 0:
        return np.zeros(num_sims), claim_counts
    
    # ── Simulation starts here ───────────────────────────────────────────
    severities = rng.lognormal(mean=mu, sigma=sigma, size=total_claims)
    
    # ── Reinsurance (XL Treaty) ───────────────────────────────────────────
    if apply_reinsurance:
        retention = params["xl_retention"]
        limit = params["xl_limit"]
        
        recoveries = np.maximum(0, np.minimum(severities - retention, limit))
        net_severities = severities - recoveries
    else:
        net_severities = severities  # no reinsurance
    
    # Build indices
    sim_indices = np.repeat(np.arange(num_sims), claim_counts)
    
    # Aggregate
    total_losses = np.bincount(
        sim_indices,
        weights=net_severities,
        minlength=num_sims
    ).astype(np.float64)

    # Note:
    # Reinsurance premium is NOT added to simulated losses.
    # It is already accounted for in capital via: net_available = GWP - expenses - RI cost
    # Losses are reduced through per-claim XL recovery, while premium reduces available funds (ruin threshold).
    
    return total_losses, claim_counts
