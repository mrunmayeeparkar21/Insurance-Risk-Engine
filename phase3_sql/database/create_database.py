"""
create_database.py
==================
Generates synthetic insurance data and builds insurance_data.db.

Run: python database/create_database.py
"""

import sqlite3
import os
import numpy as np
import pandas as pd
from datetime import date, timedelta

# ── Reproducibility ───────────────────────────────────────────
rng = np.random.default_rng(42)

# ── Paths ─────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "insurance_data.db")
SQL_PATH = os.path.join(BASE_DIR, "schema.sql")

# ── Constants (mirror inputs.py exactly) ─────────────────────
N_POLICIES    = 50_000
TARGET_GWP    = 10_00_00_000
AVG_PREMIUM   = TARGET_GWP / N_POLICIES
CLAIM_FREQ    = 0.01
MEAN_SEVERITY = 1_20_000
SEVERITY_CV   = 1.5
ANALYSIS_YEAR = 2023

PRODUCTS  = ["Motor", "Property", "Liability"]
PROD_WGTS = [0.60,    0.25,       0.15]

REGIONS   = ["North", "South", "East", "West", "Central"]
REG_WGTS  = [0.22,    0.20,    0.18,   0.22,   0.18]

STATUSES     = ["Active", "Lapsed", "Cancelled"]
STATUS_WGTS  = [0.85,     0.10,     0.05]

CLAIM_STATUSES = ["Open", "Closed", "Reopened"]
CL_ST_WGTS     = [0.30,   0.65,     0.05]


# =============================================================
# HELPER FUNCTIONS
# =============================================================

def random_date(start: date, end: date, size: int) -> np.ndarray:
    delta   = (end - start).days
    offsets = rng.integers(0, delta, size=size)
    return np.array([start + timedelta(days=int(d)) for d in offsets])


def earned_premium_fraction(start: date, end: date,
                             year: int = ANALYSIS_YEAR) -> float:
    yr_start      = date(year, 1, 1)
    yr_end        = date(year, 12, 31)
    overlap_start = max(start, yr_start)
    overlap_end   = min(end,   yr_end)
    if overlap_end < overlap_start:
        return 0.0
    policy_days  = (end - start).days or 1
    overlap_days = (overlap_end - overlap_start).days + 1
    return min(overlap_days / policy_days, 1.0)


def lognormal_params(mean: float, cv: float):
    sigma2 = np.log(1 + cv ** 2)
    mu     = np.log(mean) - 0.5 * sigma2
    return mu, np.sqrt(sigma2)


# =============================================================
# TABLE 1 — policies
# =============================================================

def build_policies() -> pd.DataFrame:
    print("  Building policies table ...")

    policy_ids    = [f"POL-{i+1:05d}" for i in range(N_POLICIES)]
    product_types = rng.choice(PRODUCTS, size=N_POLICIES, p=PROD_WGTS)
    regions       = rng.choice(REGIONS,  size=N_POLICIES, p=REG_WGTS)
    statuses      = rng.choice(STATUSES, size=N_POLICIES, p=STATUS_WGTS)

    sum_insured = np.where(
        product_types == "Motor",
            rng.uniform(2_00_000,   15_00_000,  N_POLICIES),
        np.where(
            product_types == "Property",
                rng.uniform(10_00_000, 2_00_00_000, N_POLICIES),
                rng.uniform(5_00_000,  50_00_000,   N_POLICIES)
        )
    )

    mu_p, sig_p = lognormal_params(AVG_PREMIUM, 0.60)
    raw_premium = rng.lognormal(mu_p, sig_p, N_POLICIES)
    raw_premium = raw_premium * (TARGET_GWP / raw_premium.sum())

    start_dates = random_date(date(2022, 1, 1), date(2023, 6, 30), N_POLICIES)
    end_dates   = np.array([s + timedelta(days=365) for s in start_dates])

    ep_fracs    = np.array([
        earned_premium_fraction(s, e)
        for s, e in zip(start_dates, end_dates)
    ])
    earned_prem = raw_premium * ep_fracs

    df = pd.DataFrame({
        "policy_id":      policy_ids,
        "product_type":   product_types,
        "region":         regions,
        "sum_insured":    np.round(sum_insured, 2),
        "annual_premium": np.round(raw_premium, 2),
        "start_date":     [str(d) for d in start_dates],
        "end_date":       [str(d) for d in end_dates],
        "earned_premium": np.round(earned_prem, 2),
        "status":         statuses,
    })

    print(f"    -> {len(df):,} policies | "
          f"GWP = Rs {df['annual_premium'].sum()/1e7:.2f} Cr | "
          f"Avg premium = Rs {df['annual_premium'].mean():,.0f}")
    return df


# =============================================================
# TABLE 2 — claims
# =============================================================

def build_claims(policies: pd.DataFrame) -> pd.DataFrame:
    print("  Building claims table ...")

    exposed  = policies[
        policies["status"] != "Cancelled"
    ]["policy_id"].values
    n_claims = int(round(len(exposed) * CLAIM_FREQ))

    claimant_ids = rng.choice(exposed, size=n_claims, replace=False)

    mu_s, sig_s  = lognormal_params(MEAN_SEVERITY, SEVERITY_CV)
    gross_losses = rng.lognormal(mu_s, sig_s, n_claims)
    gross_losses = gross_losses * (MEAN_SEVERITY / gross_losses.mean())
    gross_losses = np.round(gross_losses, 2)

    claim_types = np.where(
        gross_losses < 2_00_000, "Attritional",
        np.where(
            gross_losses < 5_00_000, "Large",
            "Catastrophe"
        )
    )

    cl_statuses = rng.choice(CLAIM_STATUSES, size=n_claims, p=CL_ST_WGTS)
    paid_frac   = np.where(
        cl_statuses == "Closed",
            1.0,
            rng.uniform(0.40, 0.75, n_claims)
    )
    paid_losses     = np.round(gross_losses * paid_frac, 2)
    reserved_losses = np.round(gross_losses - paid_losses, 2)

    claim_dates    = random_date(
        date(2023, 1, 1), date(2023, 12, 31), n_claims
    )
    report_lags    = rng.integers(0, 90, size=n_claims)
    reported_dates = np.array([
        d + timedelta(days=int(lag))
        for d, lag in zip(claim_dates, report_lags)
    ])

    df = pd.DataFrame({
        "claim_id":      [f"CLM-{i+1:05d}" for i in range(n_claims)],
        "policy_id":     claimant_ids,
        "claim_date":    [str(d) for d in claim_dates],
        "reported_date": [str(d) for d in reported_dates],
        "gross_loss":    gross_losses,
        "paid_loss":     paid_losses,
        "reserved_loss": reserved_losses,
        "claim_type":    claim_types,
        "status":        cl_statuses,
    })

    freq = len(df) / len(policies)
    print(f"    -> {len(df):,} claims | "
          f"Frequency = {freq:.4f} | "
          f"Mean severity = Rs {df['gross_loss'].mean():,.0f}")

    type_pct = df["claim_type"].value_counts(normalize=True)
    for t, p in type_pct.items():
        print(f"       {t}: {p:.1%}")

    return df


# =============================================================
# TABLE 3 — reinsurance_treaties
# =============================================================

def build_reinsurance_treaties() -> pd.DataFrame:
    print("  Building reinsurance_treaties table ...")

    # Reinsurance programme stored for structural realism.
    # Current stochastic model explicitly applies only XL per-risk cover.
    # Quota share and stop-loss treaties are included for future extension.

    data = [
        {
            "treaty_id":        "TRT-001",
            "treaty_type":      "XL_Per_Risk",
            "attachment_point": 5_00_000,
            "limit_amount":     45_00_000,
            "cession_rate":     None,
            "ri_premium":       TARGET_GWP * 0.08,
            "effective_date":   "2023-01-01",
            "expiry_date":      "2023-12-31",
        },
        {
            "treaty_id":        "TRT-002",
            "treaty_type":      "Quota_Share",
            "attachment_point": None,
            "limit_amount":     None,
            "cession_rate":     0.20,
            "ri_premium":       TARGET_GWP * 0.20 * 0.30,
            "effective_date":   "2023-01-01",
            "expiry_date":      "2023-12-31",
        },
        {
            "treaty_id":        "TRT-003",
            "treaty_type":      "Stop_Loss",
            "attachment_point": TARGET_GWP * 0.70,
            "limit_amount":     TARGET_GWP * 0.20,
            "cession_rate":     None,
            "ri_premium":       TARGET_GWP * 0.015,
            "effective_date":   "2023-01-01",
            "expiry_date":      "2023-12-31",
        },
    ]

    df = pd.DataFrame(data)
    print(f"    -> {len(df)} reinsurance treaties loaded")
    return df


# =============================================================
# TABLE 4 — underwriting_years
# =============================================================

def build_underwriting_years(policies: pd.DataFrame,
                              claims:   pd.DataFrame) -> pd.DataFrame:
    print("  Building underwriting_years table ...")

    ibnr_factors = {
        2019: 0.02,
        2020: 0.05,
        2021: 0.08,
        2022: 0.12,
        2023: 0.18,
    } 
    product_ibnr_base = {
        "Motor": 1.0,
        "Property": 1.1,
        "Liability": 1.4
    }
    rows = []

    for uw_year in range(2019, 2024):
        for product in PRODUCTS:
            prod_weight = dict(zip(PRODUCTS, PROD_WGTS))[product]
            year_scale  = rng.uniform(0.85, 1.15)

            policies_written = int(N_POLICIES * prod_weight * year_scale)
            gwp_yr           = TARGET_GWP * prod_weight * year_scale
            earned_yr        = gwp_yr * rng.uniform(0.90, 1.00)

            n_claims = int(
                policies_written
                * CLAIM_FREQ
                * rng.uniform(0.85, 1.15)
            )
            
            mean_sev_yr = MEAN_SEVERITY * rng.uniform(0.90, 1.10)
            # true ultimate loss
            ultimate = n_claims * mean_sev_yr
            
            # maturity assumptions by underwriting year
            paid_pct_map = {
                2019: 0.96,
                2020: 0.88,
                2021: 0.76,
                2022: 0.62,
                2023: 0.45,
            }
            
            case_pct_map = {
                2019: 0.02,
                2020: 0.05,
                2021: 0.10,
                2022: 0.16,
                2023: 0.22,
            }
            
            paid_pct = paid_pct_map[uw_year]
            
            case_pct = (
                case_pct_map[uw_year]
                * product_ibnr_base[product]
                * rng.uniform(0.9, 1.1)
            )
            
            # keep realistic bounds
            case_pct = min(case_pct, 0.35)
            
            paid = ultimate * paid_pct
            case_reserve = ultimate * case_pct
            incurred = paid + case_reserve
            
            # hidden IBNR
            ibnr = ultimate - incurred
            
            loss_ratio = incurred / earned_yr
            combined_ratio = loss_ratio + 0.30 + 0.08

            rows.append({
                "uw_year":          uw_year,
                "product_type":     product,
                "policies_written": policies_written,
                "gwp":              round(gwp_yr, 2),
                "earned_premium":   round(earned_yr, 2),
                "reported_claims":  n_claims,
                "paid_loss":        round(paid, 2),
                "case_reserve":     round(case_reserve, 2),
                "incurred_loss":    round(incurred, 2),
                "ibnr_estimate":    round(ibnr, 2),
                "loss_ratio":       round(incurred / earned_yr, 4),
                "combined_ratio":   round((incurred / earned_yr) + 0.30 + 0.08, 4),
            })

    df = pd.DataFrame(rows)
    print(f"    -> {len(df)} underwriting year rows "
          f"({df['uw_year'].nunique()} years x "
          f"{df['product_type'].nunique()} products)")
    return df

# =============================================================
# TABLE 5 — claims_development
# =============================================================

def build_claims_development(uw_df: pd.DataFrame) -> pd.DataFrame:
    print("  Building claims_development table ...")

    development_patterns = {
        2019: {12: 0.82, 24: 0.93, 36: 0.98, 48: 0.995, 60: 1.00},
        2020: {12: 0.78, 24: 0.90, 36: 0.96, 48: 0.99},
        2021: {12: 0.70, 24: 0.85, 36: 0.94},
        2022: {12: 0.58, 24: 0.76},
        2023: {12: 0.46},
    }

    rows = []
    uw_summary = (
        uw_df.groupby("uw_year")["paid_loss"]
        .sum()
        .reset_index()
    )

    for _, row in uw_summary.iterrows():
        uw_year = row["uw_year"]
        latest_paid = row["paid_loss"]

        maturity = max(development_patterns[uw_year].values())
        estimated_ultimate = latest_paid / maturity

        for dev_month, pct_paid in development_patterns[uw_year].items():
            cumulative_paid = estimated_ultimate * pct_paid

            rows.append({
                "uw_year": uw_year,
                "development_month": dev_month,
                "cumulative_paid": round(cumulative_paid, 2),
            })

    df = pd.DataFrame(rows)
    print(f"    -> {len(df)} claims development rows created")
    return df

# =============================================================
# DATABASE WRITER + MAIN
# =============================================================

def write_to_db(conn:  sqlite3.Connection,
                df:    pd.DataFrame,
                table: str) -> None:
    df.to_sql(table, conn, if_exists="replace", index=False)
    print(f"    Wrote {len(df):,} rows -> '{table}'")


def main():
    print("=" * 60)
    print("  Insurance Risk Engine — Database Builder")
    print("=" * 60)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"  Removed existing: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    with open(SQL_PATH, "r") as f:
        conn.executescript(f.read())
    print("  Schema applied.")
    print()

    policies = build_policies()
    claims   = build_claims(policies)
    ri       = build_reinsurance_treaties()
    uw       = build_underwriting_years(policies, claims)
    dev      = build_claims_development(uw)

    print()
    print("  Writing to database ...")
    write_to_db(conn, policies, "policies")
    write_to_db(conn, claims,   "claims")
    write_to_db(conn, ri,       "reinsurance_treaties")
    write_to_db(conn, uw,       "underwriting_years")
    write_to_db(conn, dev,      "claims_development")

    conn.commit()
    conn.close()

    size_mb = os.path.getsize(DB_PATH) / 1_048_576
    print()
    print(f"  Database built : {DB_PATH}  ({size_mb:.1f} MB)")
    print()
    print("  Next steps:")
    print("    python database/extract_inputs.py")
    print("    python tests/test_database.py")
    print("=" * 60)


if __name__ == "__main__":
    main()