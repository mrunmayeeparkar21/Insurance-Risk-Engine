# insurance_risk_engine/mle_analysis.py

import numpy as np
import pandas as pd
import sqlite3
from scipy import stats


def run_mle_analysis(db_path):

    with sqlite3.connect(db_path) as conn:
        claims_df = pd.read_sql("SELECT gross_loss FROM claims", conn)
        exposure_df = pd.read_sql("""SELECT COUNT(*) as n FROM policies WHERE status != 'Cancelled'""", conn)

    gross_losses = claims_df["gross_loss"].values
    n_claims = len(gross_losses)
    n_exposed = exposure_df["n"].iloc[0]

    # ───────────── Frequency ─────────────
    lambda_mle = n_claims / n_exposed
    lambda_se = np.sqrt(lambda_mle / n_exposed)
    ci_low = lambda_mle - 1.96 * lambda_se
    ci_high = lambda_mle + 1.96 * lambda_se

    model_freq = 0.01
    dev_freq = (lambda_mle - model_freq) / model_freq

    # ───────────── Severity ─────────────
    log_losses = np.log(gross_losses)
    mu = log_losses.mean()
    sigma = log_losses.std(ddof=1)

    mu_se = sigma / np.sqrt(n_claims)
    sigma_se = sigma / np.sqrt(2 * (n_claims - 1))

    mean = np.exp(mu + sigma**2 / 2)
    cv = np.sqrt(np.exp(sigma**2) - 1)

    mu_model = np.log(120000) - 0.5 * np.log(1 + 1.5**2)
    sigma_model = np.sqrt(np.log(1 + 1.5**2))

    dev_mu = (mu - mu_model) / mu_model * 100
    dev_sigma = (sigma - sigma_model) / sigma_model * 100

    # ───────────── GOF ─────────────
    ks_stat, p_value = stats.kstest(
        gross_losses,
        "lognorm",
        args=(sigma, 0, np.exp(mu))
    )

    # ───────────── OUTPUT ─────────────
    return {
        "n_exposed": n_exposed,
        "n_claims": n_claims,
        "lambda": lambda_mle,
        "ci": (ci_low, ci_high),
        "dev_freq": dev_freq,

        "mu": mu,
        "sigma": sigma,
        "mu_se": mu_se,
        "sigma_se": sigma_se,
   
        "mean": mean,
        "cv": cv,
        "mu_model": mu_model,
        "sigma_model": sigma_model,
        "dev_mu": dev_mu,
        "dev_sigma": dev_sigma,

        "ks_stat": ks_stat,
        "p_value": p_value,

        "gross_losses": gross_losses
    }
