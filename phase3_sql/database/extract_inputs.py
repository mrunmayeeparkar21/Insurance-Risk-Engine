"""
extract_inputs.py
-----------------
Queries insurance_data.db and compares derived actuarial
assumptions against the hardcoded values in inputs.py.

Run: python notebooks/database/extract_inputs.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "insurance_data.db")

MODEL_ASSUMPTIONS = {
    "num_policies":    50_000,
    "gwp":             10_00_00_000,
    "claim_frequency": 0.01,
    "mean_severity":   1_20_000,
    "loss_ratio":      0.60,
}

# Validation uses all policies to match PORTFOLIO model assumption of 50,000 total in-force
def extract_from_database() -> dict:
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(DISTINCT p.policy_id),
            ROUND(SUM(p.annual_premium), 0),
            ROUND(COUNT(c.claim_id) * 1.0 
                  / (SELECT COUNT(*) FROM policies 
            WHERE status != 'Cancelled'), 4),
            ROUND(AVG(c.gross_loss), 0),
            ROUND(SUM(c.gross_loss)
                  / SUM(p.annual_premium), 4)
        FROM policies p
        LEFT JOIN claims c ON p.policy_id = c.policy_id
    """)
    row = cursor.fetchone()
    conn.close()

    return {
        "num_policies":    int(row[0]),
        "gwp":             float(row[1]),
        "claim_frequency": float(row[2]),
        "mean_severity":   float(row[3] or 0),
        "loss_ratio":      float(row[4] or 0),
    }


def print_comparison(derived: dict) -> None:
    print()
    print("=" * 70)
    print("  Phase 3 -> Phase 2 Pipeline Validation")
    print("  Derived from database  vs  Hardcoded in inputs.py")
    print("=" * 70)
    print(f"  {'Metric':<28} {'Derived':>14} {'Model':>14} {'Dev%':>7}")
    print("  " + "-" * 65)

    all_ok = True

    for key, model_val in MODEL_ASSUMPTIONS.items():
        derived_val = derived[key]
        deviation   = ((derived_val - model_val) / model_val * 100
                       if model_val != 0 else 0.0)
        flag        = "  <-- REVIEW" if abs(deviation) > 5 else ""

        if flag:
            all_ok = False

        if key == "gwp":
            d_str = f"Rs{derived_val/1e7:>8.2f} Cr"
            m_str = f"Rs{model_val/1e7:>8.2f} Cr"
        elif key == "num_policies":
            d_str = f"{int(derived_val):>14,}"
            m_str = f"{int(model_val):>14,}"
        elif key == "mean_severity":
            d_str = f"Rs{derived_val:>11,.0f}"
            m_str = f"Rs{model_val:>11,.0f}"
        else:
            d_str = f"{derived_val:>14.4f}"
            m_str = f"{model_val:>14.4f}"

        print(f"  {key:<28} {d_str} {m_str} {deviation:>6.1f}%{flag}")

    print("=" * 70)
    if all_ok:
        print("  RESULT: All deviations within 5% tolerance.")
        print("          Database is consistent with Phase 2 model.")
    else:
        print("  RESULT: One or more deviations exceed 5%.")
        print("          Review flagged assumptions.")
    print("=" * 70)
    print()


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print("ERROR: insurance_data.db not found.")
        print("Run: python notebooks/database/create_database.py first.")
    else:
        derived = extract_from_database()
        print_comparison(derived)