# Phase 3 — SQL Data Pipeline

## Overview

A relational SQLite database containing synthetic insurance data for 50,000 policies
and ~500 claims, with an automated parameter extraction pipeline that feeds directly
into the Phase 2 Python model. This phase introduces proper separation between data
storage, actuarial modelling, and reporting.

---

## Database Schema

```
policies              claims               reinsurance_treaties
─────────────────     ──────────────────   ────────────────────
policy_id (PK)        claim_id (PK)        treaty_id (PK)
product_type          policy_id (FK)       treaty_type
region                claim_date           attachment_point
sum_insured           reported_date        limit_amount
annual_premium        gross_loss           cession_rate
start_date            paid_loss            ri_premium
end_date              reserved_loss        effective_date
earned_premium        claim_type           expiry_date
status                status

underwriting_years                claims_development
──────────────────────────────    ──────────────────────
uw_year (PK)                      uw_year (PK)
product_type (PK)                 development_month (PK)
policies_written                  cumulative_paid
gwp / earned_premium
paid_loss / case_reserve
incurred_loss / ibnr_estimate
loss_ratio / combined_ratio
```

---

## File Reference

| File                    | Purpose                                                           |
|-------------------------|-------------------------------------------------------------------|
| `schema.sql`            | CREATE TABLE statements for all 5 tables                          |
| `create_database.py`    | Generates synthetic data and builds `insurance_data.db`           |
| `extract_inputs.py`     | Validates database against model assumptions (deviation flags)    |
| `extract_parameters.py` | Returns a PORTFOLIO-compatible parameter dict for the Python model|
| `queries.sql`           | 8 actuarial SQL queries for portfolio analysis                    |
| `tests/test_database.py`| 8 automated verification tests for data integrity                 |

---

## Database Statistics

| Table                 | Rows   | Notes                                        |
|-----------------------|--------|----------------------------------------------|
| policies              | 50,000 | Motor (60%), Property (25%), Liability (15%) |
| claims                | ~476   | Empirical frequency ≈ 1.00% (exposed basis)  |
| reinsurance_treaties  | 3      | XL per-risk, Quota Share, Stop-Loss          |
| underwriting_years    | 15     | 5 years × 3 product types (2019–2023)        |
| claims_development    | 14     | Dynamic paid development triangle            |

### Model Validation (extract_inputs.py output)

| Metric            | From Database | Model Assumption | Deviation |
|-------------------|--------------|-----------------|-----------|
| Policy Count      | 50,000       | 50,000          | 0.0%      |
| GWP               | ₹10.00 Cr    | ₹10.00 Cr       | < 0.1%    |
| Claim Frequency   | 1.0004%      | 1.0000%         | < 0.1%    |
| Mean Severity     | ₹1,20,000    | ₹1,20,000       | < 0.1%    |
| Loss Ratio        | ~60%         | 60%             | < 1%      |

---

## SQL Queries (queries.sql)

| Query | Description                                            |
|-------|--------------------------------------------------------|
| 1     | Portfolio overview — GWP and policy count by segment   |
| 2     | Empirical claim frequency by product and region        |
| 3     | Severity distribution by claim type (with empirical CV)|
| 4     | Loss ratio analysis by product type                    |
| 5     | XL reinsurance recovery analysis (per-risk treaty)     |
| 6     | Large loss report — top 20 claims ranked by gross loss |
| 7     | Underwriting year development (maturity staging)       |
| 8     | Model input extraction — the pipeline query            |

> **Note on Query 4 denominator:** Annual premium is used as the loss ratio
> denominator (not earned premium) because the synthetic claim data represents
> full-year losses rather than exposure-apportioned claims. Using earned premium
> on this dataset would inflate the reported loss ratio relative to the model's
> design intent.

---

## Parameter Pipeline

`extract_parameters.py` connects the database directly to the Python model:

```python
from phase3_sql.database.extract_parameters import extract_parameters
params = extract_parameters()   # Returns PORTFOLIO-compatible dict
losses, _ = run_monte_carlo(params=params)
```

Extracted parameters:
- `num_policies` — active (non-cancelled) exposed count
- `claim_frequency` — observed claims / exposed policies
- `mean_severity` — mean gross loss
- `severity_cv` — empirical sample coefficient of variation

Fixed parameters (not extracted from DB):
- `gross_written_premium`, `expense_ratio`, `ri_cost_ratio`
- `xl_retention`, `xl_limit`, `available_capital`, `management_buffer`

---

## Automated Tests (test_database.py)

Eight tests run on every database build:

| Test | Description                               | Tolerance |
|------|-------------------------------------------|-----------|
| 1    | Policy count = 50,000                     | Exact     |
| 2    | Claim frequency ≈ 1.00%                   | ±0.2%     |
| 3    | Mean severity ≈ ₹1,20,000                 | ±5%       |
| 4    | All 5 tables populated above minimum rows | Exact     |
| 5    | Attritional claims ≥ 70% of mix           | Exact     |
| 6    | XL reinsurance query executes correctly   | Exact     |
| 7    | Underwriting years span 2019–2023         | Exact     |
| 8    | Total GWP ≈ ₹10 Cr                        | ±1%       |

---

## Basic Reconciliation Note

Historical underwriting-year loss ratios in the SQL/Power BI dataset are calculated on an earned-premium basis across multiple accident and underwriting years, while the Phase 1 and Phase 2 actuarial models use a simplified prospective pricing assumption of 60% loss ratio on gross written premium. The figures are therefore not directly comparable and are intended for different analytical purposes (historical portfolio analysis vs forward-looking risk modelling).
Simulated claim severities are rescaled post-generation to preserve the target portfolio mean severity. This introduces mild compression in realised sample CV estimates recovered through MLE.

---

## How to Run

```bash
# Step 1: Build the database (run from project root)
python phase3_sql/database/create_database.py

# Step 2: Validate against model assumptions
python phase3_sql/database/extract_inputs.py

# Step 3: Run automated tests
python phase3_sql/tests/test_database.py

# Step 4: Run SQL queries directly
sqlite3 phase3_sql/database/insurance_data.db < phase3_sql/database/queries.sql
```

---

## Design Decisions

- **One claim per policy maximum** — synthetic dataset uses sampling without
  replacement. This is noted in query comments. Real multi-claim datasets would
  require premium aggregation separately from the LEFT JOIN.
- **XL treaty modelled stochastically** — Quota Share and Stop-Loss treaties
  exist in the `reinsurance_treaties` table for future extension but are
  intentionally excluded from current stochastic loss modelling.
- **Severity rescaling** — gross losses are rescaled to force arithmetic mean
  to exactly ₹1,20,000. This preserves shape but slightly alters distributional
  properties, causing a ~5% deviation between MLE lognormal mean and model mean.
