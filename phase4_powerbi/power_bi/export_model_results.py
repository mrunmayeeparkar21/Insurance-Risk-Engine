"""
export_model_results.py
-----------------------
Exports Insurance Risk Engine model results to CSV for Power BI.
Runs all three scenarios and exports every metric the dashboard needs.

Run from project root: python power_bi/export_model_results.py
"""
import sys
import os
import csv
import sqlite3
from datetime import date

# Add project root to path so we can import the package
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from phase2_python.insurance_risk_engine.inputs              import PORTFOLIO, SIMULATION
from phase2_python.insurance_risk_engine.deterministic_model import run_deterministic_model
from phase2_python.insurance_risk_engine.stochastic_model    import run_monte_carlo
from phase2_python.insurance_risk_engine.risk_metrics        import compute_risk_metrics

POWER_BI_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_OUT = os.path.join(POWER_BI_DIR, "model_results.csv")
DB_PATH = os.path.join(PROJECT_ROOT, "database", "insurance_data.db")

SCENARIOS = {
    "Base": PORTFOLIO,
    "Optimistic": {
        **PORTFOLIO,
        "claim_frequency": 0.005,
        "mean_severity":   100000,
    },
    "Stress": {
        **PORTFOLIO,
        "claim_frequency": 0.02,
        "mean_severity":   150000,
        "severity_cv":     2.0,
    },
}

def run_scenario(name, params):
    print(f"  Running scenario: {name} ...")
    det = run_deterministic_model(params)
    losses, _ = run_monte_carlo(params)
    metrics = compute_risk_metrics(losses, params)

    return {
        # Identifiers
        "scenario": name,
        "run_date": str(date.today()),

        # Portfolio inputs
        "gross_written_premium": params["gross_written_premium"],
        "num_policies": params["num_policies"],
        "claim_frequency": params["claim_frequency"],
        "mean_severity": params["mean_severity"],
        "severity_cv": params.get("severity_cv", PORTFOLIO["severity_cv"]),
        "expense_ratio": params["expense_ratio"],
        "ri_cost_ratio": params["ri_cost_ratio"],
        "xl_retention": params["xl_retention"],
        "available_capital": params["available_capital"],

        # Deterministic outputs
        "expected_claim_count": det["expected_claim_count"],
        "expected_gross_loss": det["expected_gross_loss"],
        "expenses": det["expenses"],
        "ri_cost": det["ri_cost"],
        "net_profit": det["net_profit"],
        "loss_ratio": det["loss_ratio"],
        "combined_ratio": det["combined_ratio"],

        # Stochastic risk metrics
        "mean_loss": metrics["mean_loss"],
        "std_dev": metrics["std_dev"],
        "var_95": metrics["var_95"],
        "var_99": metrics["var_99"],
        "var_99_5": metrics["var_99_5"],
        "es_95": metrics["es_95"],
        "es_99": metrics["es_99"],
        "ruin_probability": metrics["ruin_probability"],
        "net_available": metrics["net_available"],

        # Capital adequacy
        "scr": metrics["scr"],
        "management_buffer": metrics["management_buffer"],
        "total_capital_required": metrics["total_capital_required"],
        "solvency_ratio": metrics["solvency_ratio"],
        "rorc": metrics["rorc"],
    }

def export_sql_tables():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database file not found at {DB_PATH}")
        print("Please run 'python database/create_database.py' first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    tables = ["policies", "claims", "reinsurance_treaties", "underwriting_years"]
    for table in tables:
        out_path = os.path.join(POWER_BI_DIR, f"{table}.csv")

        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]

        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

        print(f"  Exported {table:<22} rows: {len(rows):,} → {table}.csv")

    conn.close()

def main():
    print("=" * 55)
    print("Insurance Risk Engine — Power BI Data Export")
    print("=" * 55)
    print(f"Simulations per scenario: {SIMULATION['num_sims']:,}")
    print(f"Output path: {CSV_OUT}\n")

    rows = []
    for name, params in SCENARIOS.items():
        rows.append(run_scenario(name, params))

    fieldnames = list(rows[0].keys())
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported model results CSV with {len(rows)} rows and {len(fieldnames)} columns.\n")

    print("Exporting SQL tables to CSV...")
    export_sql_tables()

    print("\nExport complete!")

if __name__ == "__main__":
    main()