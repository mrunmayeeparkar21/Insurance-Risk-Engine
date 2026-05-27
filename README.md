# Insurance Risk Engine
### End-to-End Actuarial Risk Modelling — Non-Life Insurance Portfolio

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![SQL](https://img.shields.io/badge/SQL-SQLite-green)](https://sqlite.org)
[![Excel](https://img.shields.io/badge/Excel-VBA--Free-217346)](https://microsoft.com/excel)
[![Power BI](https://img.shields.io/badge/Power%20BI-Dashboard-F2C811)](https://powerbi.microsoft.com)

**Actuarial Analyst Portfolio Project | Non-Life Insurance | India**

---

## Project Overview

A complete actuarial risk model for a ₹10 Crore gross written premium non-life insurance
portfolio, built end-to-end across four phases using industry-standard tools and
methodologies. The project answers five core business questions:

1. **Is the portfolio profitable?**
2. **How risky is it under normal conditions?**
3. **What happens under stress scenarios?**
4. **How likely is an extreme loss event?**
5. **Is the company holding sufficient capital?**

---

## Project Architecture

```
Phase 1: Excel       →  Deterministic pricing, 5,000-run simulation, VaR/SCR, dashboard
         ↓
Phase 2: Python      →  Monte Carlo (100,000 scenarios), MLE calibration,
         ↓              stochastic XL reinsurance, IBNR (Chain-Ladder + BF)
Phase 3: SQL         →  SQLite database (50,000 policies, ~500 claims),
         ↓              parameter extraction, pipeline validation
Phase 4: Power BI    →  Interactive executive dashboard, scenario analysis,
                        capital adequacy monitoring
```

---

## Key Results

All figures below are from the Phase 2 Python stochastic model (100,000 Monte Carlo
simulations, MLE-calibrated parameters). See the cross-phase note below for the
difference between Excel and Python capital metrics.

### Underwriting Performance (Deterministic)

| Metric                  | Value       | Benchmark  | Status       |
|-------------------------|-------------|------------|--------------|
| Gross Written Premium   | ₹10.00 Cr   | —          | —            |
| Expected Claim Count    | 500         | —          | —            |
| Expected Loss           | ₹6.00 Cr    | —          | —            |
| Loss Ratio              | 60.0%       | < 60%      | ⚠ At limit   |
| Expense Ratio           | 30.0%       | < 35%      | ✓ OK         |
| Combined Ratio          | 98.0%       | < 100%     | ⚠ Watch      |
| Net Underwriting Profit | ₹20 lakh    | > 0        | ✓ Profitable |

### Stochastic Risk Metrics (Python, 100,000 Simulations, MLE Parameters)

| Metric                           | Value       | Notes                           |
|----------------------------------|-------------|---------------------------------|
| Mean Loss (Gross)                | ₹5.98 Cr    | MLE-calibrated lognormal        |
| VaR 95%                          | ₹6.81 Cr    | 1-in-20 year loss               |
| VaR 99%                          | ₹7.19 Cr    | 1-in-100 year loss              |
| VaR 99.5% (Solvency II basis)    | ₹7.34 Cr    | 1-in-200 year loss              |
| Expected Shortfall 99%           | ₹7.41 Cr    | Mean of tail beyond VaR 99%     |
| Technical Insolvency Probability | 0.01%       | Losses > net premiums + capital |
| Net VaR 99% (post XL)            | ₹6.32 Cr    | After XL reinsurance recovery   |
| Net VaR 99.5% (post XL)          | ₹6.43 Cr    | After XL reinsurance recovery   |

### Capital Adequacy (Python Stochastic Model)

| Metric                      | Value    | Threshold | Status                 |
|-----------------------------|----------|-----------|------------------------|
| SCR (VaR 99.5% − E[L])      | ₹1.36 Cr | —         | Economic capital basis |
| Total Capital Required      | ₹1.64 Cr | —         | SCR + 20% buffer       |
| Available Capital           | ₹2.00 Cr | —         | —                      |
| Solvency Ratio              | 1.22×    | ≥ 1.5×    | ⚠ Below target         |
| RORC                        | 13.3%    | ≥ 10%     | ✓ Adequate             |

### MLE Parameter Calibration

| Parameter               | MLE Estimate | Model Prior | Deviation |
|-------------------------|--------------|-------------|-----------|
| Claim Frequency (λ)     | 0.0100       | 0.0100      | < 1%      |
| Severity µ (log-scale)  | 11.176       | 11.106      | +0.6%     |
| Severity σ (log-scale)  | 1.064        | 1.086       | −2.0%     |
| KS Test p-value         | 0.37         | —           | ✓ Pass    |

### IBNR Reserving

| Method                          | IBNR Estimate |
|---------------------------------|---------------|
| Chain-Ladder                    | ₹1.86 Cr     |
| Bornhuetter-Ferguson            | ₹2.58 Cr      |
| Credibility-Weighted (blended)  | ₹2.01 Cr      |

---

## Cross-Phase Capital Note

The Excel model (Phase 1) uses simplified **deterministic severity** — each simulated
claim is assigned the mean severity of ₹1,20,000 rather than a random lognormal draw.
This compresses the loss distribution substantially, producing:

- Excel VaR 99.5% = **₹6.71 Cr** → Solvency = **2.35×** (appears comfortable)

The Python model (Phase 2) applies **full lognormal severity sampling** (CV = 1.5),
which captures severity volatility and fat-tail risk, producing:

- Python VaR 99.5% = **₹7.34 Cr** → Solvency = **1.22×** (below 1.5× management target)

This divergence is a primary finding of the project: the simplified Excel model
materially understates tail risk and leads to an overstatement of capital adequacy.
The Python stochastic result is the more credible figure for risk management purposes.

---

## Phase Summaries

### Phase 1 — Excel Deterministic Model
10-sheet workbook with deterministic underwriting P&L, Poisson-normal Monte Carlo
simulation (5,000 iterations), sensitivity tornado chart, pricing adequacy test with
capital charge, and SCR-based solvency framework.

### Phase 2 — Python Stochastic Engine

**Collective Risk Model:**
```
S = X₁ + X₂ + ... + X_N
where N ~ Poisson(λ = 476),  Xᵢ ~ Lognormal(µ = 11.176, σ = 1.064)
```
Fully vectorised using `np.bincount` — 50 million severity draws processed
in a single NumPy call. 100,000 Monte Carlo scenarios in under 3 seconds.

**Stochastic XL Reinsurance:**
```
Recovery per claim = MAX(0, MIN(severity − ₹5,00,000, ₹45,00,000))
```

**MLE Parameter Estimation** — frequency (Poisson) and severity (lognormal) fitted
directly from the SQLite database using `scipy.stats`. KS goodness-of-fit test
conducted as an in-sample diagnostic (p = 0.37).

**IBNR Reserving** — Dynamic chain-ladder with volume-weighted age-to-age factors
across 5 underwriting years (2019–2023), blended with Bornhuetter-Ferguson using
development maturity (percent-reported) as credibility weights.

### Phase 3 — SQL Data Pipeline
SQLite database with 5 relational tables (policies, claims, underwriting years,
claims development, reinsurance treaties). Eight actuarial SQL queries covering
portfolio overview, frequency/severity segmentation, reinsurance recovery, large
loss report, and model input extraction. Includes an automated parameter extraction
pipeline with deviation-flag validation against model assumptions.

### Phase 4 — Power BI Dashboard
Three-page interactive dashboard: Executive Summary, Tail Risk Analysis, and
Portfolio Analytics. Scenario slicer (Base / Optimistic / Stress), dynamic risk
metrics, solvency gauge, loss distribution chart, and reinsurance impact panel.

---

## Repository Structure

```
insurance-risk-engine/
│
├── phase1_excel/
│   ├── insurance_risk_model.xlsx
│   └── README.md
│
├── phase2_python/
│   ├── insurance_risk_engine/
│   │   ├── inputs.py
│   │   ├── deterministic_model.py
│   │   ├── stochastic_model.py
│   │   ├── mle_analysis.py
│   │   ├── risk_metrics.py
│   │   ├── optimization.py
│   │   ├── reinsurance.py
│   │   ├── reserving.py
│   │   ├── visualizations.py
│   │   └── main.py
│   ├── notebooks/
│   │   └── full_analysis.ipynb
│   └── README.md
│
├── phase3_sql/
│   ├── database/
│   │   ├── schema.sql
│   │   ├── create_database.py
│   │   ├── extract_inputs.py
│   │   ├── extract_parameters.py
│   │   └── queries.sql
│   ├── tests/
|   |   ├── test_database.py
│   │   └── test_model.py
│   └── README.md
│
├── phase4_powerbi/
│   ├── power_bi_insurance_risk_dashboard.pbix
│   └── README.md
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## How to Run

```bash
# 1. Clone the repository
git clone https://github.com/mrunmayeeparkar21/Insurance-Risk-Engine.git
cd Insurance-Risk-Engine

# 2. Create and activate a virtual environment (recommended)
python -m venv actuarial_env
# Windows:
actuarial_env\Scripts\activate
# macOS/Linux:
source actuarial_env/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Build the SQLite database
python phase3_sql/database/create_database.py
python phase3_sql/database/extract_inputs.py

# 5. Run the full Python pipeline
python -m phase2_python.insurance_risk_engine.main

# 6. Run the Jupyter notebook (full analysis with charts)
jupyter notebook phase2_python/notebooks/full_analysis.ipynb

# 7. Run database tests
python phase3_sql/tests/test_database.py
```

> **Note:** The Power BI dashboard (`.pbix`) requires Power BI Desktop.
> Run `phase4_powerbi/power_bi/export_model_results.py` to regenerate
> the CSV files that feed the dashboard before opening it.

---

## Skills Demonstrated

| Category   | Tools & Techniques                                                      |
|------------|-------------------------------------------------------------------------|
| Actuarial  | Collective Risk Model, VaR, Expected Shortfall, SCR, Ruin Probability, XL Reinsurance, Chain-Ladder, Bornhuetter-Ferguson, MLE, Pricing Adequacy |
| Python     | NumPy vectorisation, Monte Carlo simulation, scipy.optimize, scipy.stats, pandas, matplotlib, seaborn |
| SQL        | Relational schema design, 8 actuarial queries, pipeline validation, LEFT JOIN aggregation |
| Excel      | Simulation, sensitivity tornado, dashboard design, capital framework    |
| Power BI   | DAX measures, scenario slicers, interactive visuals, executive reporting |

---

## Model Limitations

The following are known simplifications that would be addressed in a production model:

- Claim frequency assumes **independent Poisson arrivals**; correlated catastrophe clustering is not modelled
- Only **lognormal severity** was fitted; alternatives (Pareto, Burr, Weibull) were not tested
- The **XL reinsurance model** covers the per-risk treaty only; quota share and stop-loss treaties are excluded from stochastic modelling
- **IBNR estimates** are point estimates without confidence intervals
- **No multi-year projection** or claims inflation loading
- The **chain-ladder tail factor** (1.02) is a simplifying assumption, not benchmarked to external data
- **Ruin probability** is defined as technical insolvency (aggregate losses exceeding net premium resources plus available capital), rather than simple underwriting loss probability

---

## Requirements

```
numpy>=1.24
pandas>=2.0
matplotlib>=3.7
seaborn>=0.12
scipy>=1.10
openpyxl>=3.1
jupyter>=1.0
nbformat>=5.0
```
