# Phase 1 — Excel Deterministic Pricing Model

## Overview

A 10-sheet Excel workbook implementing a deterministic underwriting model and a
simplified Monte Carlo simulation for a ₹10 Crore non-life insurance portfolio.
This phase establishes baseline profitability, capital adequacy, and sensitivity
metrics before progressing to the full stochastic Python engine in Phase 2.

---

## Workbook Structure

| Sheet               | Purpose                                                                       |
|---------------------|-------------------------------------------------------------------------------|
| Management Summary  | One-page executive overview with automated risk status flags                  |
| Inputs              | All user-editable assumptions; scenario selector (Base / Optimistic / Stress) |
| Calculations        | Underwriting P&L, key ratios, reinsurance recovery analysis                   |
| Sensitivity Analysis| One-way shocks to frequency, severity, expenses; tornado chart                |
| Pricing Adequacy    | Required premium build-up including capital cost charge                       |
| Capital & Solvency  | SCR computation, solvency ratio, capital surplus/(shortfall)                  |
| Simulation          | 5,000-iteration Poisson-normal Monte Carlo; VaR, ruin probability             |
| Scenarios           | Side-by-side Base / Optimistic / Stress comparison                            |
| Charts              | Loss distribution histogram, tornado chart, scenario bar chart                |
| Data                | Lookup tables supporting scenario and ratio calculations                      |

---

## Key Results (Base Case)

| Metric                   | Value       | Benchmark  | Status             |
|--------------------------|-------------|------------|--------------------|
| Gross Written Premium    | ₹10.00 Cr   | —          | —                  |
| Expected Claim Count     | 500         | —          | —                  | 
| Expected Loss            | ₹6.00 Cr    | —          | —                  |
| Loss Ratio               | 60.0%       | < 60%      | ⚠ At limit         |
| Expense Ratio            | 30.0%       | < 35%      | ✓ OK               |
| Combined Ratio           | 98.0%       | < 100%     | ⚠ Watch            |
| Net Underwriting Profit  | ₹20 lakh    | > 0        | ✓ Profitable       |
| VaR 99.5% (simulation)   | ₹6.71 Cr    | —          | Solvency II basis  |
| SCR                      | ₹71 lakh    | —          | Unexpected loss    |
| Solvency Ratio           | 2.39×       | ≥ 1.0×     | ✓ Solvent          |
| Pricing Adequacy Ratio   | 0.982×      | ≥ 1.0×     | ✗ Under-priced     |
| Required Rate Increase   | ~1.8%       | 0%         | Action needed       |

---

## Methodology

### Underwriting P&L
Standard combined ratio decomposition:
```
Net Profit = GWP − Expected Loss − Expenses − RI Cost
           = ₹10.00 Cr − ₹6.00 Cr − ₹3.00 Cr − ₹0.80 Cr
           = ₹0.20 Cr (₹20 lakh)
```

### Monte Carlo Simulation (Simulation Sheet)
The simulation uses a **normal approximation to the Poisson distribution** (valid
since λ = 500 >> 30, CLT applies) for claim count, and applies **mean severity**
deterministically per simulation. This is a simplified approach — severity volatility
is not modelled. The Phase 2 Python engine replaces this with full lognormal severity
sampling, which is why capital metrics differ between the two phases.

```
Claim Count  ~  Normal(µ = 500, σ = √500 ≈ 22.4)
Simulated Loss = Claim Count × ₹1,20,000 (deterministic severity)
```

### Pricing Adequacy
Required premium built up from first principles:
```
Required Premium = Pure Loss Cost + Expenses + RI Cost + Risk Margin + Capital Cost
                 = ₹6.00 Cr + ₹3.00 Cr + ₹0.80 Cr + ₹0.18 Cr + ₹0.20 Cr
                 = ₹1,01,80,000
```
Current premium (₹1,00,00,000) falls short by ₹1,80,000 → ~1.8% rate increase needed.

### Capital Framework
```
SCR  = VaR(99.5%) − E[Loss]  =  ₹6.71 Cr − ₹6.00 Cr  =  ₹71 lakh
TCR  = SCR × (1 + 20% buffer)                           =  ₹85 lakh
Solvency Ratio = Available Capital / TCR = ₹2.00 Cr / ₹0.84 Cr = 2.39×
```

### Key Risk Drivers (Sensitivity / Tornado)
1. **Claim Frequency** — ±30% swing produces a ₹3.6 Cr profit swing (largest driver)
2. **Claim Severity** — ±20% swing produces a ₹2.4 Cr profit swing
3. **Expense Ratio** — 20%→40% range produces a ₹2.0 Cr profit swing
4. **RI Cost Ratio** — 5%→11% range produces a ₹0.6 Cr swing

### Important Limitation
At mean severity ₹1,20,000, the XL treaty attachment point (₹5,00,000) is never
triggered under base case assumptions. The XL treaty provides **no protection** for
attritional claims — it is designed for large individual losses. This is explicitly
flagged on the Calculations sheet. 
Capital Cost assumes a simplified 10% charge on available capital held
against underwriting risk (₹2 Cr × 10% = ₹20 lakh). This is an illustrative
management pricing load, not a regulatory cost-of-capital calibration.

---

## How to Use

1. Open `insurance_risk_model.xlsx` in Microsoft Excel
2. Navigate to the **Inputs** sheet and select a scenario from the dropdown
3. All dependent sheets recalculate automatically
4. Review the **Management Summary** for the automated risk status assessment
5. Use the **Sensitivity Analysis** sheet to stress individual assumptions
