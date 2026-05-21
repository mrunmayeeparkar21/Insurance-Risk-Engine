# insurance_risk_engine/main.py

import os
import numpy as np
import pandas as pd
import sqlite3

# Core modules
from phase2_python.insurance_risk_engine.inputs import PORTFOLIO, SIMULATION
from phase2_python.insurance_risk_engine.deterministic_model import run_deterministic_model
from phase2_python.insurance_risk_engine.stochastic_model import (
    run_monte_carlo,
    get_lognormal_params,
)
from phase2_python.insurance_risk_engine.risk_metrics import compute_risk_metrics
from phase2_python.insurance_risk_engine.optimization import (
    premium_for_breakeven,
    premium_for_target_ruin,
    premium_for_target_combined_ratio,
)
from phase2_python.insurance_risk_engine.visualizations import (
    plot_loss_distribution,
    plot_severity_comparison,
    plot_stress_scenarios,
    plot_summary_dashboard,
    plot_mle_fit,
    plot_ibnr_chain_ladder,
)

# SQL + Advanced
from phase3_sql.database.extract_parameters import extract_parameters
from phase2_python.insurance_risk_engine.mle_analysis import run_mle_analysis
from phase2_python.insurance_risk_engine.reinsurance import simulate_xl_reinsurance
from phase2_python.insurance_risk_engine.reserving import (
    load_underwriting_data,
    load_claims_development,
    build_triangle,
    chain_ladder_summary,
    ibnr_comparison,
    capital_impact,
)

D = "=" * 60


def _cr(v):
    return f"Rs {v/1e7:>7.2f} Cr"


def _pc(v):
    return f"{v:>8.2f}%"


SCENARIOS = {
    "Base": PORTFOLIO,
    "Optimistic": {
        **PORTFOLIO,
        "claim_frequency": 0.005,
        "mean_severity": 1_00_000,
    },
    "Stress": {
        **PORTFOLIO,
        "claim_frequency": 0.020,
        "mean_severity": 1_50_000,
        "severity_cv": 2.0,
    },
}


def main():
    print("\nInsurance Risk Engine — FULL PIPELINE RUN\n")

    # =========================
    # 1. DETERMINISTIC MODEL
    # =========================
    print(f"{D}\n1. DETERMINISTIC MODEL\n{D}")
    det = run_deterministic_model()

    print(f"Gross Written Premium: {_cr(det['gross_written_premium'])}")
    print(f"Expected Claims:       {det['expected_claim_count']:.0f}")
    print(f"Expected Loss:         {_cr(det['expected_gross_loss'])}")
    print(f"Expenses:              {_cr(det['expenses'])}")
    print(f"RI Cost:               {_cr(det['ri_cost'])}")
    print(f"Net Profit:            {_cr(det['net_profit'])}")
    print(f"Loss Ratio:            {_pc(det['loss_ratio']*100)}")
    print(f"Combined Ratio:        {_pc(det['combined_ratio']*100)}")

    # =========================
    # 2. PARAMETER EXTRACTION (SQL)
    # =========================
    print(f"\n{D}\n2. SQL PARAMETER EXTRACTION\n{D}")
    params = extract_parameters()

    for k, v in params.items():
        print(f"{k}: {v}")

    print("\nUsing SQL-derived exposure/frequency assumptions:")
    print(f"  Claim Frequency: {params['claim_frequency']:.4f}")
    print(f"  Severity Mean:   Rs {params['mean_severity']:.0f}")
    
    print("\nSeverity distribution calibrated separately via MLE fit.")
    print("Alternative heavy-tail distributions (e.g. Pareto/Burr) were not tested;")
    print("lognormal was selected as the benchmark severity model for this project.")

    # =========================
    # 3. MLE ANALYSIS
    # =========================
    print(f"\n{D}\n3. MLE ANALYSIS\n{D}")
    mle_params = run_mle_analysis("phase3_sql/database/insurance_data.db")
    ks_pass = "PASS" if mle_params["p_value"] > 0.05 else "FAIL"

    print("MLE completed.")
    print(f"Poisson Frequency MLE:              {mle_params['lambda']:.4f}")
    print(f"95% Frequency CI:                   ({mle_params['ci'][0]:.4f} - {mle_params['ci'][1]:.4f})")
    print(f"Frequency deviation vs SQL assumption: {mle_params['dev_freq']:.2%}")
    print(f"Mu deviation vs MoM calibration:    {mle_params['dev_mu']:.2f}%")
    print(f"Sigma deviation vs MoM calibration: {mle_params['dev_sigma']:.2f}%")
    print(f"Mu standard error:                  {mle_params['mu_se']:.4f}")
    print(f"Sigma standard error:               {mle_params['sigma_se']:.4f}")
    print(f"KS Statistic:                       {mle_params['ks_stat']:.4f}")
    print(f"KS p-value (in-sample diagnostic):  {mle_params['p_value']:.4f}")
    print("Note: KS test uses fitted parameters from the same sample and is treated as an exploratory goodness-of-fit diagnostic, not formal out-of-sample validation.")
    
    # =========================
    # 4. MONTE CARLO SIMULATION
    # =========================
    print(f"\n{D}\n4. MONTE CARLO SIMULATION\n{D}")
    
    mc_params = params.copy()
    # Poisson frequency MLE + lognormal severity MLE
    mc_params["claim_frequency"] = mle_params["lambda"]
    mc_params["mu"] = mle_params["mu"]
    mc_params["sigma"] = mle_params["sigma"]
    
    # Gross simulation
    losses, _ = run_monte_carlo(params=mc_params)

    # Net-of-reinsurance simulation
    net_losses, _ = run_monte_carlo(
        params=mc_params,
        apply_reinsurance=True
    )

    print("\nNote: Simulation uses fitted parameters, not static portfolio assumptions.")

    print(f"Mean Loss: {_cr(losses.mean())}")
    print(f"Std Dev:   {_cr(losses.std())}")
    print("Model assumption: claim frequency follows independent Poisson arrivals; correlated catastrophe clustering is outside current scope.")

    # =========================
    # 5. RISK METRICS
    # =========================
    print(f"\n{D}\n5. RISK METRICS\n{D}")
    m = compute_risk_metrics(losses, mc_params)
    net_var_99 = np.percentile(net_losses, 99)
    net_var_995 = np.percentile(net_losses, 99.5)

    print(f"Mean Loss:              {_cr(m['mean_loss'])}")
    print(f"VaR 95%:                {_cr(m['var_95'])}")
    print(f"VaR 99%:                {_cr(m['var_99'])}")
    print(f"VaR 99.5%:              {_cr(m['var_99_5'])}")
    print(f"Net VaR 99% (post XL):  {_cr(net_var_99)}")
    print(f"Net VaR 99.5% (post XL): {_cr(net_var_995)}")
    print(f"Expected Shortfall:     {_cr(m['es_99'])}")
    print(f"Economic Ruin Probability: {_pc(m['ruin_probability']*100)}")

    # ====================================
    # 6. UNDERWRITING CAPITAL ADEQUACY
    # ====================================
    print(f"\n{D}\n6. CAPITAL ADEQUACY\n{D}")
    print(f"Underwriting Economic Capital Proxy: {_cr(m['scr'])}")
    print(f"Internal Capital Target:{_cr(m['total_capital_required'])}")
    print(f"Available Capital:      {_cr(PORTFOLIO['available_capital'])}")
    print(f"Management Solvency Ratio: {m['solvency_ratio']:.2f}x")
    print(f"RORC:                   {_pc(m['rorc']*100)}")
    
    if m["solvency_ratio"] < 1.5:
        shortfall = (1.5 * m["total_capital_required"] - PORTFOLIO["available_capital"])
        print(f"Observation: Portfolio appears materially undercapitalised "
              f"relative to a 1.5x solvency target.")
        print(f"Estimated capital shortfall: {_cr(shortfall)}")
        print("Management actions may include capital injection, "
              "premium repricing, portfolio de-risking, or expanded reinsurance protection.")
    
    print("Note: Economic capital proxy based on unexpected underwriting loss above expected loss; not a full Solvency II or IRDAI regulatory SCR calculation.")
    print("Model progression note: Excel phase used deterministic average severity for illustration,")
    print("whereas Python uses full stochastic lognormal severity simulation, producing materially higher tail risk and capital requirements.")

    # =========================
    # 7. PREMIUM OPTIMISATION
    # =========================
    print(f"\n{D}\n7. PREMIUM OPTIMISATION\n{D}")
    be = premium_for_breakeven(base_params=mc_params)
    rp = premium_for_target_ruin(0.05, base_params=mc_params)
    cr = premium_for_target_combined_ratio(0.95, base_params=mc_params)
    cur = PORTFOLIO["gross_written_premium"]

    print(f"Current Premium:         {_cr(cur)}")
    print(f"Break-even Premium:      {_cr(be)}")
    print(f"5% Ruin Target Premium:  {_cr(rp)}")
    print(f"Premium for 95% Combined Ratio Target: {_cr(cr)}")
    print(f"Ruin Pricing Change:     {_pc((rp/cur-1)*100)}")
    print(f"CR Pricing Change:       {_pc((cr/cur-1)*100)}")

    # =========================
    # 8. STRESS TESTING
    # =========================
    print(f"\n{D}\n8. STRESS TESTING\n{D}")
    stress_results = {}

    for name, p in SCENARIOS.items():
        stress_mc = p.copy()
        
        if name == "Base":
            stress_mc["mu"] = mle_params["mu"]
            stress_mc["sigma"] = mle_params["sigma"]
        else:
            mu, sigma = get_lognormal_params(
                stress_mc["mean_severity"],
                stress_mc["severity_cv"]
            )
            
            stress_mc["mu"] = mu
            stress_mc["sigma"] = sigma
        
        l, _ = run_monte_carlo(params=stress_mc)
        r = compute_risk_metrics(l, stress_mc)
        stress_results[name] = r

        print(
            f"{name:10s} | VaR99: {_cr(r['var_99'])} | "
            f"Ruin: {r['ruin_probability']:.2%} | "
            f"Solvency: {r['solvency_ratio']:.2f}x"
        )

    # ============================
    # 9. VAR STABILITY BOOTSTRAP
    # ============================
    print(f"\n{D}\n9. VAR STABILITY (BOOTSTRAP)\n{D}")
    rng_boot = np.random.default_rng(99)
    boot = []
    
    for _ in range(1000):
        sample = rng_boot.choice(losses, size=len(losses), replace=True)
        boot.append(np.percentile(sample, 99))
        
    ci_low, ci_high = np.percentile(boot, [2.5, 97.5])
        
    print(f"VaR 99%: {_cr(np.percentile(losses, 99))}")
    print(f"95% CI:  {_cr(ci_low)} – {_cr(ci_high)}")
    print("Note: This measures simulation stability, not parameter uncertainty.")
    
    # ===============================
    # 10. PARAMETER SENSITIVITY (MLE)
    # ===============================
    print(f"\n{D}\n10. PARAMETER SENSITIVITY (MLE)\n{D}")
    
    mu = mle_params["mu"]
    sigma = mle_params["sigma"]
    mu_se = mle_params["mu_se"]
    sigma_se = mle_params["sigma_se"]
    
    sensitivity = []
    
    for label, mu_test, sigma_test in [
        ("Lower Bound", mu - mu_se, max(0.01, sigma - sigma_se)),
        ("Upper Bound", mu + mu_se, sigma + sigma_se),
    ]:
        test_params = mc_params.copy()
        test_params["mu"] = mu_test
        test_params["sigma"] = sigma_test
        
        test_losses, _ = run_monte_carlo(params=test_params)
        test_metrics = compute_risk_metrics(test_losses, test_params)
        
        sensitivity.append({
            "Scenario": label,
            "VaR 99% (Rs Cr)": round(test_metrics["var_99"] / 1e7, 3),
            "VaR 99.5% (Rs Cr)": round(test_metrics["var_99_5"] / 1e7, 3),
            "SCR (Rs Cr)": round(test_metrics["scr"] / 1e7, 3),
        })
        
    print(pd.DataFrame(sensitivity).to_string(index=False))

    # =========================
    # 11. REINSURANCE ANALYSIS
    # =========================
    print(f"\n{D}\n11. REINSURANCE ANALYSIS\n{D}")

    res = simulate_xl_reinsurance(mle_params=mle_params)
    ri_cost = PORTFOLIO["gross_written_premium"] * PORTFOLIO["ri_cost_ratio"]

    print(f"RI Premium Cost:    {_cr(ri_cost)}")
    print(f"Expected Recovery:  {_cr(res['annual_recovery'].mean())}")
    print(f"Ruin (Gross):       {res['ruin_gross']:.2%}")
    print(f"Ruin (Net):         {res['ruin_net']:.2%}")
    print("Scope: XL per-risk treaty only (quota share / stop loss excluded).")
    print("Observation: Treaty reduces tail risk, but current attachment may be economically expensive under observed severity assumptions.")

    # =========================
    # 12. IBNR RESERVING
    # =========================
    print(f"\n{D}\n12. IBNR RESERVING\n{D}")

    uw = load_underwriting_data("phase3_sql/database/insurance_data.db")
    dev = load_claims_development("phase3_sql/database/insurance_data.db")

    # Chain Ladder
    tri = build_triangle(dev)
    cl = chain_ladder_summary(dev)

    # Chain Ladder + Bornhuetter-Ferguson comparison
    ibnr_table, ibnr_blended = ibnr_comparison(cl, uw)

    # Capital impact after reserving
    capital_table, capital_post_ibnr, solvency_post = capital_impact(
        ibnr_blended,
        PORTFOLIO,
        m
    )
    
    print(ibnr_table.to_string(index=False))
    print()
    print(capital_table.to_string(index=False))
    print()
    print(f"Post-IBNR Solvency Ratio: {solvency_post:.2f}x")
    
    if capital_post_ibnr < 0:
        print(
            f"Observation: Post-IBNR capital is negative, implying "
            f"a reserve strengthening requirement of {_cr(abs(capital_post_ibnr))}."
        )
    elif solvency_post < 1.5:
        print(
            "Observation: Portfolio remains materially undercapitalised "
            "after reserve strengthening."
        )
        
    print("IBNR calculation completed.")

    # =========================
    # 13. VISUALIZATIONS
    # =========================
    print(f"\n{D}\n13. GENERATING CHARTS\n{D}")
    plot_severity_comparison(PORTFOLIO, save=True)
    plot_loss_distribution(losses, m, save=True)
    plot_stress_scenarios(stress_results, save=True)
    plot_summary_dashboard(m, det, save=True)
    plot_mle_fit(mle_params, save=True)
    plot_ibnr_chain_ladder(cl, save=True) 

    # =========================
    # FINAL CHECK
    # =========================
    print(f"\n{D}\nFINAL CHECK\n{D}")
    charts = [
        "outputs/loss_distribution.png",
        "outputs/severity_comparison.png",
        "outputs/stress_scenarios.png",
        "outputs/summary_dashboard.png",
        "outputs/mle_goodness_of_fit.png",
        "outputs/ibnr_chain_ladder.png"
    ]

    for c in charts:
        print(f"{'✓' if os.path.exists(c) else '✗'} {c}")

    # =========================
    # KEY FINDINGS
    # =========================
    print(f"\n{D}\nKEY FINDINGS\n{D}")
    print(f"Mean Loss: {_cr(m['mean_loss'])}")
    print(f"VaR 99%:   {_cr(m['var_99'])}")
    print(f"ES 99%:    {_cr(m['es_99'])}")
    print(f"Ruin Prob: {_pc(m['ruin_probability']*100)}")
    print(f"Solvency:  {m['solvency_ratio']:.2f}x")

    print("\nPipeline execution complete.\n")


if __name__ == "__main__":
    main() 