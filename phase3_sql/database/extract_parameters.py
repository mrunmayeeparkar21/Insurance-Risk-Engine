"""
extract_parameters.py
---------------------
Queries insurance_data.db and returns a complete
PORTFOLIO-compatible parameter dictionary for use
in run_monte_carlo() and compute_risk_metrics().
"""
import sqlite3
import pandas as pd
import os

# These are the fixed assumptions that do not
# come from the database
FIXED_ASSUMPTIONS = {
    "gross_written_premium": 10_00_00_000,
    "expense_ratio":         0.30,
    "ri_cost_ratio":         0.08,   
    "xl_retention":          5_00_000,
    "xl_limit":              45_00_000,
    "available_capital":     2_00_00_000,
    "management_buffer":     0.20,
}


def extract_parameters(db_path=None) -> dict:
    """
    Extract claim frequency, mean severity and CV
    from the database. Merge with fixed assumptions
    to return a complete PORTFOLIO-compatible dict.
    """
    if db_path is None:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        db_path  = os.path.join(BASE_DIR, "insurance_data.db")

    conn     = sqlite3.connect(db_path)
    claims   = pd.read_sql("SELECT * FROM claims",   conn)
    policies = pd.read_sql("SELECT * FROM policies", conn)
    conn.close()

    num_policies    = len(policies [policies["status"] != "Cancelled"])
    num_claims      = len(claims)
    claim_frequency = num_claims / num_policies
    mean_severity   = claims["gross_loss"].mean()
    std_severity    = claims["gross_loss"].std()
    severity_cv     = std_severity / mean_severity
    # severity_cv is the empirical sample CV from observed claims.
    # Monte Carlo severity simulation uses MLE-fitted lognormal
    # parameters (mu, sigma), which may differ from this raw CV.

    print("  Extracted parameters from database:")
    print(f"    Policies:         {num_policies:,}")
    print(f"    Claims:           {num_claims:,}")
    print(f"    Frequency:        {claim_frequency:.4f}")
    print(f"    Mean Severity:    Rs {mean_severity:,.0f}")
    print(f"    Severity CV:      {severity_cv:.2f}")

    params = {
        **FIXED_ASSUMPTIONS,
        "num_policies":    num_policies,
        "claim_frequency": claim_frequency,
        "mean_severity":   mean_severity,
        "severity_cv":     severity_cv,
    }

    return params