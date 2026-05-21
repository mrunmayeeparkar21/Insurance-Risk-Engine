# insurance_risk_engine/reserving.py

import sqlite3
import pandas as pd
import os


def load_underwriting_data(db_path: str) -> pd.DataFrame:
    """Load underwriting years table from database."""
    with sqlite3.connect(db_path) as conn:
        uw_df = pd.read_sql("""
            SELECT uw_year, product_type,
                   gwp, earned_premium,
                   paid_loss,
                   case_reserve,
                   incurred_loss,
                   ibnr_estimate,
                   loss_ratio,
                   combined_ratio
            FROM underwriting_years
            ORDER BY uw_year, product_type
        """, conn)
    return uw_df


def load_claims_development(db_path: str) -> pd.DataFrame:
    """Load claims development triangle data."""
    with sqlite3.connect(db_path) as conn:
        dev_df = pd.read_sql("""
            SELECT
                uw_year,
                development_month,
                cumulative_paid
            FROM claims_development
            ORDER BY uw_year, development_month
        """, conn)

    dev_df["uw_year"] = dev_df["uw_year"].astype(int)

    return dev_df

def build_triangle(dev_df: pd.DataFrame) -> pd.DataFrame:
    """Build cumulative paid development triangle."""
    triangle = dev_df.pivot(
        index="uw_year",
        columns="development_month",
        values="cumulative_paid"
    )

    triangle = triangle.sort_index()
    triangle = triangle.sort_index(axis=1)

    return triangle

def calculate_development_factors(triangle: pd.DataFrame) -> dict:
    """Calculate age-to-age development factors dynamically."""
    factors = {}

    dev_periods = list(triangle.columns)

    for i in range(len(dev_periods) - 1):
        curr = dev_periods[i]
        nxt = dev_periods[i + 1]

        valid = triangle[[curr, nxt]].dropna()

        factor = valid[nxt].sum() / valid[curr].sum()

        factors[(curr, nxt)] = factor

    return factors

def calculate_cdfs(factors: dict, tail_factor: float = 1.02) -> dict:
    """Convert age-to-age development factors into cumulative development factors.
    Tail factor default of 1.02 is a simplifying assumption chosen for this predominantly short-tail synthetic portfolio. 
    For long-tail liability business, materially higher tail assumptions would be appropriate and should be calibrated from external benchmarks or development history."""
    
    cdfs = {}

    ordered_periods = sorted(set(
        period[0] for period in factors.keys()
    ))

    for period in ordered_periods:
        cdf = tail_factor

        curr = period

        while True:
            next_links = [
                k for k in factors.keys()
                if k[0] == curr
            ]

            if not next_links:
                break

            next_link = next_links[0]

            cdf *= factors[next_link]

            curr = next_link[1]

        cdfs[period] = cdf

    return cdfs
    
    
def chain_ladder_summary(dev_df: pd.DataFrame) -> pd.DataFrame:
    """Run dynamic chain ladder reserving."""

    triangle = build_triangle(dev_df)

    factors = calculate_development_factors(triangle)

    cdfs = calculate_cdfs(factors)

    rows = []

    for uw_year in triangle.index:
        row = triangle.loc[uw_year]

        latest_dev = row.last_valid_index()

        latest_paid = row[latest_dev]

        ult_factor = cdfs.get(latest_dev, 1.02)

        ultimate_loss = latest_paid * ult_factor

        ibnr = ultimate_loss - latest_paid

        rows.append({
            "uw_year": uw_year,
            "latest_dev_month": latest_dev,
            "paid_loss": latest_paid,
            "ult_factor": ult_factor,
            "ultimate_loss": ultimate_loss,
            "ibnr_cl": ibnr,
        })

    return pd.DataFrame(rows)


def ibnr_comparison(
    cl_results: pd.DataFrame,
    uw_df: pd.DataFrame,
    a_priori_lr: float = None,
) -> tuple:
    """Compare Chain Ladder vs Bornhuetter-Ferguson."""
    
    if a_priori_lr is None:
        a_priori_lr = 0.60  # blended synthetic portfolio prior, aligned with deterministic underwriting LR

    total_ibnr_cl = cl_results["ibnr_cl"].sum()
    total_ibnr_db = uw_df.groupby("uw_year")["ibnr_estimate"].sum().sum()

    earned_by_year = (
        uw_df.groupby("uw_year")["earned_premium"]
        .sum()
        .reset_index()
    )

    bf_ibnr = 0
    weighted_ibnr = 0

    # Credibility-weighted blend based on development maturity.
    # Chain Ladder weight = % reported
    # Bornhuetter-Ferguson weight = % unreported
    for _, row in cl_results.iterrows():
        cl_ibnr = row["ibnr_cl"]

        earned = earned_by_year.loc[
            earned_by_year["uw_year"] == row["uw_year"],
            "earned_premium"
        ].values[0]

        expected_ultimate = earned * a_priori_lr
        percent_reported = 1 / row["ult_factor"]
        bf_reserve = expected_ultimate * (1 - percent_reported)

        bf_ibnr += bf_reserve

        cl_weight = percent_reported
        bf_weight = 1 - percent_reported

        blended_reserve = (
            cl_weight * cl_ibnr
            + bf_weight * bf_reserve
        )

        weighted_ibnr += blended_reserve

    ibnr_blended = weighted_ibnr

    ibnr_summary = pd.DataFrame({
        "Method": [
            "Bornhuetter-Ferguson",
            "Chain-Ladder",
            "Database Estimate",
        ],
        "IBNR (Rs Cr)": [
            round(bf_ibnr / 1e7, 3),
            round(total_ibnr_cl / 1e7, 3),
            round(total_ibnr_db / 1e7, 3),
        ],
    })

    return ibnr_summary, ibnr_blended


def capital_impact(
    ibnr_blended: float,
    portfolio:    dict,
    metrics:      dict,
) -> tuple:
    """Calculate capital adequacy after IBNR."""
    available_capital = portfolio["available_capital"]
    
    # Simplified assumption: Blended IBNR reduces available surplus capital directly.
    capital_post_ibnr = available_capital - ibnr_blended
    
    solvency_post = (capital_post_ibnr
        / metrics["total_capital_required"]
    )

    capital_table = pd.DataFrame({
        "Metric": [
            "Available Capital",
            "IBNR Liability",
            "Capital After IBNR",
        ],
        "Amount (Rs Cr)": [
            round(available_capital / 1e7, 3),
            round(ibnr_blended / 1e7, 3),
            round(capital_post_ibnr / 1e7, 3),
        ],
    })

    return capital_table, capital_post_ibnr, solvency_post


def prepare_ibnr_data(dev_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare dynamic chain ladder data for charts."""
    return chain_ladder_summary(dev_df)
