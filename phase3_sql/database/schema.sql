-- =============================================================
-- Insurance Risk Engine — Database Schema
-- =============================================================

CREATE TABLE IF NOT EXISTS policies (
    policy_id      TEXT PRIMARY KEY,
    product_type   TEXT NOT NULL,
    region         TEXT NOT NULL,
    sum_insured    REAL NOT NULL,
    annual_premium REAL NOT NULL,
    start_date     DATE NOT NULL,
    end_date       DATE NOT NULL,
    earned_premium REAL NOT NULL,
    status         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id      TEXT PRIMARY KEY,
    policy_id     TEXT NOT NULL,
    claim_date    DATE NOT NULL,
    reported_date DATE NOT NULL,
    gross_loss    REAL NOT NULL,
    paid_loss     REAL NOT NULL,
    reserved_loss REAL NOT NULL,
    claim_type    TEXT NOT NULL,
    status        TEXT NOT NULL,
    FOREIGN KEY (policy_id) REFERENCES policies(policy_id)
);

CREATE TABLE IF NOT EXISTS reinsurance_treaties (
    treaty_id        TEXT PRIMARY KEY,
    treaty_type      TEXT NOT NULL,
    attachment_point REAL,
    limit_amount     REAL,
    cession_rate     REAL,
    ri_premium       REAL NOT NULL,
    effective_date   DATE NOT NULL,
    expiry_date      DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS underwriting_years (
    uw_year          INTEGER NOT NULL,
    product_type     TEXT    NOT NULL,
    policies_written INTEGER NOT NULL,
    gwp              REAL    NOT NULL,
    earned_premium   REAL    NOT NULL,
    reported_claims  INTEGER NOT NULL,
    incurred_loss    REAL    NOT NULL,
    paid_loss        REAL    NOT NULL,
    case_reserve      REAL    NOT NULL,
    ibnr_estimate    REAL    NOT NULL,
    loss_ratio       REAL    NOT NULL,
    combined_ratio   REAL    NOT NULL,
    PRIMARY KEY (uw_year, product_type)
);

CREATE TABLE IF NOT EXISTS claims_development (
    uw_year             INTEGER NOT NULL,
    development_month   INTEGER NOT NULL,
    cumulative_paid     REAL    NOT NULL,
    PRIMARY KEY (uw_year, development_month)
);