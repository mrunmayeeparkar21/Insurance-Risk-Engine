# Phase 2 — Python Stochastic Risk Engine

## Overview

A full stochastic actuarial risk engine built in Python, implementing a
Poisson–Lognormal collective risk model with 100,000 Monte Carlo simulations.
This phase supersedes the simplified Excel simulation by introducing:

- Per-claim lognormal severity sampling (replacing deterministic mean severity)
- MLE parameter calibration from the SQLite database
- Stochastic XL reinsurance recovery
- Full capital adequacy and premium optimisation
- Chain-Ladder + Bornhuetter-Ferguson IBNR reserving

---

## Module Reference

| Module                  | Purpose                                                        |
|-------------------------|----------------------------------------------------------------|
| `inputs.py`             | All hardcoded portfolio and simulation parameters              |
| `deterministic_model.py`| Replicates the Excel P&L calculation exactly                   |
| `stochastic_model.py`   | Collective risk model Monte Carlo engine                       |
| `mle_analysis.py`       | MLE fitting for Poisson frequency and lognormal severity       |
| `risk_metrics.py`       | VaR, ES, SCR, solvency ratio, ruin probability, RORC           |
| `optimization.py`       | Break-even, ruin-target, and combined-ratio premium solvers    |
| `reinsurance.py`        | Stochastic per-claim XL reinsurance simulation                 |
| `reserving.py`          | Chain-ladder, Bornhuetter-Ferguson, capital impact after IBNR  |
| `visualizations.py`     | All matplotlib/seaborn charts                                  |
| `main.py`               | Full pipeline orchestrator — runs all modules end-to-end       |

---

## Key Results (100,000 Simulations, MLE Parameters)

### Risk Metrics

| Metric                        | Gross        | Net of XL RI  |
|-------------------------------|--------------|---------------|
| Mean Loss                     | ₹5.98 Cr     | —             |
| VaR 95%                       | ₹6.81 Cr     | —             |
| VaR 99%                       | ₹7.19 Cr     | ₹6.32 Cr      |
| VaR 99.5% (Solvency II basis) | ₹7.34 Cr     | ₹6.43 Cr      |
| Expected Shortfall 99%        | ₹7.41 Cr     | —             |

### Capital Adequacy

| Metric                  | Value    | Target   | Status              |
|-------------------------|----------|----------|---------------------|
| SCR (unexpected loss)   | ₹1.36 Cr | —        | —                   |
| Total Capital Required  | ₹1.64 Cr | —        | SCR + 20% buffer    |
| Available Capital       | ₹2.00 Cr | —        | —                   |
| Solvency Ratio          | 1.22×    | ≥ 1.5×   | ⚠ Below target      |
| RORC                    | 13.3%    | ≥ 10%    | ✓ Adequate          |

> **Why does the solvency ratio differ from Phase 1 (Excel)?**
> The Excel model assigns mean severity deterministically per simulation, compressing
> the distribution. Python samples severity from a lognormal (CV = 1.5), which
> correctly captures severity volatility and produces a fatter tail.
> Excel VaR 99.5% = ₹6.71 Cr → solvency 2.35× (overstated)
> Python VaR 99.5% = ₹7.34 Cr → solvency 1.22× (more realistic)

### MLE Calibration

| Parameter         | MLE Estimate | Model Prior | Notes                         |
|-------------------|-------------|------------|-------------------------------|
| Frequency λ       | 0.0100      | 0.0100     | Exact match                   |
| Severity µ        | 11.176      | 11.106     | +0.6% deviation               |
| Severity σ        | 1.064       | 1.086      | −2.0% deviation               |
| KS p-value        | 0.37        | > 0.05     | In-sample diagnostic — ✓ Pass |

The KS test uses fitted parameters on the same sample and is treated as an
exploratory goodness-of-fit diagnostic, not formal out-of-sample validation.

### IBNR Reserving

| Method                             | IBNR Reserve |
|------------------------------------|--------------|
| Chain-Ladder                       | ₹10.13 Cr    |
| Bornhuetter-Ferguson               | ₹4.26 Cr     |
| Credibility-Weighted (blended)     | ₹7.19 Cr     |

Credibility weights use **development maturity** (percent reported) as the CL weight
and percent unreported as the BF weight — standard actuarial blending practice.
The a priori loss ratio used for BF is 60%, aligned with the deterministic model.

---

## Methodology

### Collective Risk Model

```
S = X₁ + X₂ + ... + X_N
where:
  N  ~  Poisson(λ),    λ = n_policies × claim_frequency (MLE-calibrated)
  Xᵢ ~  Lognormal(µ, σ)              (MLE-calibrated from database)
```

Implemented using fully vectorised NumPy operations:
```python
claim_counts = rng.poisson(lam=lambda_, size=num_sims)
severities   = rng.lognormal(mean=mu, sigma=sigma, size=total_claims)
total_losses = np.bincount(sim_indices, weights=severities, minlength=num_sims)
```

### XL Reinsurance

Per-claim XL recovery applied **before** aggregation (per-risk treaty):
```
Recovery = MAX(0, MIN(severity − ₹5,00,000, ₹45,00,000))
Net loss  = severity − recovery
```
RI premium is excluded from simulated losses and accounted for separately
through the ruin threshold: `net_available = GWP − expenses − RI premium`.

### Capital (SCR Definition)

```
SCR  = max(VaR(99.5%) − E[Loss], 0)    ← unexpected underwriting loss
TCR  = SCR × (1 + management buffer)   ← 20% operational buffer
Solvency Ratio = Available Capital / TCR
```

This is an **economic capital proxy**, not a full Solvency II or IRDAI regulatory
SCR calculation, which would require a net asset value shock approach.

### Premium Optimisation

Three optimisation targets solved using `scipy.optimize.brentq`:

| Target                         | Method                          |
|--------------------------------|---------------------------------|
| Break-even premium             | Deterministic (zero net profit) |
| Premium for 5% ruin target     | Stochastic (ruin probability)   |
| Premium for 95% combined ratio | Deterministic (ratio equation)  |

### Bootstrap VaR Stability

1,000 bootstrap resamples of the 100,000 simulation output assess the
stability of the VaR 99% estimate. The 95% confidence interval is reported.
This measures simulation stability, not parameter uncertainty.

---

## Running the Pipeline

```bash
# Full pipeline (all 13 sections + 6 charts)
python -m phase2_python.insurance_risk_engine.main

# Individual notebook (interactive, with inline charts)
jupyter notebook phase2_python/notebooks/full_analysis.ipynb
```

### Pipeline Sections (main.py)

1. Deterministic Model
2. SQL Parameter Extraction
3. MLE Analysis
4. Monte Carlo Simulation (Gross + Net of RI)
5. Risk Metrics
6. Capital Adequacy
7. Premium Optimisation
8. Stress Testing (Base / Optimistic / Stress)
9. VaR Stability Bootstrap
10. Parameter Sensitivity (MLE bounds)
11. Reinsurance Analysis
12. IBNR Reserving
13. Chart Generation

---

## Model Limitations

- Severity distribution: only **lognormal** fitted; Pareto/Burr/Weibull not compared
- Claim arrivals assumed **independent** (no catastrophe or contagion clustering)
- **No multi-year projection** or claims inflation loading
- Chain-ladder **tail factor (1.02)** is a simplifying assumption
- IBNR estimates are **point estimates** without confidence intervals
- Quota share and stop-loss treaties **excluded** from stochastic scope
