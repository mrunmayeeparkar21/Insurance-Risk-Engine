"""
test_database.py
----------------
Eight automated verification tests for insurance_data.db.

Run: python notebooks/tests/test_database.py
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join("notebooks", "database", "insurance_data.db")


def run_tests():
    if not os.path.exists(DB_PATH):
        print("ERROR: insurance_data.db not found.")
        print("Run: python notebooks/database/create_database.py first.")
        sys.exit(1)

    conn   = sqlite3.connect(DB_PATH)
    c      = conn.cursor()
    passed = 0
    failed = 0

    def check(description, condition, detail=""):
        nonlocal passed, failed
        if condition:
            print(f"  PASS  {description}")
            passed += 1
        else:
            print(f"  FAIL  {description}  [{detail}]")
            failed += 1

    print()
    print("=" * 60)
    print("  Insurance Risk Engine — Database Verification Tests")
    print("=" * 60)

    # Test 1: policy count
    c.execute("SELECT COUNT(*) FROM policies")
    n = c.fetchone()[0]
    check("Policy count = 50,000",
          n == 50_000,
          f"got {n:,}")

    # Test 2: claim frequency using exposed (non-cancelled) policies
    c.execute("""
        SELECT COUNT(c.claim_id) * 1.0 / (SELECT COUNT(*) FROM policies
        WHERE status != 'Cancelled')
        FROM claims c
    """)
    freq = c.fetchone()[0]

    check(
        f"Claim frequency ≈ 1.00% (got {freq:.4f})", 
        abs(freq - 0.01) < 0.002
    )

    # Test 3: mean severity within 5% of Rs 1,20,000
    c.execute("SELECT AVG(gross_loss) FROM claims")
    sev = c.fetchone()[0]
    check(f"Mean severity ≈ Rs 1,20,000 (got Rs {sev:,.0f})",
          abs(sev - 120_000) / 120_000 < 0.05)

    # Test 4: all tables populated with minimum rows
    min_rows = {
        "policies":             50_000,
        "claims":               400,
        "reinsurance_treaties": 1,
        "underwriting_years":   10,
    }
    for table, min_count in min_rows.items():
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        check(f"Table '{table}' has >= {min_count} rows (got {count})",
              count >= min_count)

    # Test 5: attritional claims >= 70%
    c.execute("""
        SELECT claim_type,
                COUNT(*) * 1.0 / (SELECT COUNT(*) FROM claims)
        FROM   claims
        GROUP  BY claim_type
    """)
    mix = dict(c.fetchall())
    attritional_pct = mix.get("Attritional", 0)
    check(f"Attritional claims >= 70% (got {attritional_pct:.1%})",
          attritional_pct >= 0.70)

    # Test 6: XL Reinsurance query runs
    c.execute("""
        SELECT COUNT(*),
                SUM(MAX(0, MIN(gross_loss - 500000, 4500000)))
        FROM claims
        WHERE gross_loss > 500000
    """)
    xl_count, ri_recovery = c.fetchone()

    check(
        f"XL query: {xl_count} large claims, recovery Rs {(ri_recovery or 0)/1e7:.2f} Cr",
        xl_count is not None and xl_count >= 0
    )

    # Test 7: underwriting years span 2019-2023
    c.execute("SELECT MIN(uw_year), MAX(uw_year) FROM underwriting_years")
    min_yr, max_yr = c.fetchone()
    check(f"Underwriting years span 2019-2023 (got {min_yr}-{max_yr})",
          min_yr == 2019 and max_yr == 2023)

    # Test 8: total GWP within 1% of Rs 10 Cr
    c.execute("SELECT SUM(annual_premium) FROM policies")
    total_gwp = c.fetchone()[0]
    check(f"Total GWP ≈ Rs 10 Cr (got Rs {total_gwp/1e7:.2f} Cr)",
          abs(total_gwp - 10_00_00_000) / 10_00_00_000 < 0.01)

    conn.close()

    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        print("\n  Fix the above failures before committing to GitHub.")
        sys.exit(1)
    else:
        print("\n  All tests passed. SQL phase verification complete.")


if __name__ == "__main__":
    run_tests()