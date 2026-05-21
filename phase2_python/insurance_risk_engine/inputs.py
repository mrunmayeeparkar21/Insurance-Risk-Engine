# insurance_risk_engine/inputs.py

PORTFOLIO = {
    "gross_written_premium": 100_000_000,
    "num_policies":          50_000,
    "claim_frequency":       0.01,
    "mean_severity":         120_000,
    "severity_cv":           1.5,
    "expense_ratio":         0.30,
    "ri_cost_ratio":         0.08,   # XL per-risk treaty only; quota share + stop-loss excluded from current stochastic scope
    "xl_retention":          500_000,
    "xl_limit":              4_500_000,
    "available_capital":     20_000_000,
    "management_buffer":     0.20,
}

SIMULATION = {
    "num_sims":    100_000,
    "random_seed_mc": 42,
    "random_seed_reinsurance": 99,
}
