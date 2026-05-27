-- =============================================================
-- Insurance Risk Engine — Actuarial SQL Analysis
-- Phase 3: Data Layer Queries
-- Database: insurance_data.db (SQLite)
-- =============================================================

-- QUERY 1: Portfolio Overview
SELECT
    product_type,
    region,
    COUNT(*) AS policy_count,
    ROUND(SUM(annual_premium) / 1e7, 2) AS gwp_crore,
    ROUND(AVG(annual_premium), 0) AS avg_premium_rs,
    ROUND(SUM(earned_premium) / 1e7, 2) AS earned_premium_crore,
    COUNT(CASE WHEN status = 'Active' THEN 1 END) AS active,
    COUNT(CASE WHEN status = 'Lapsed' THEN 1 END) AS lapsed,
    COUNT(CASE WHEN status = 'Cancelled' THEN 1 END) AS cancelled
FROM policies
GROUP BY product_type, region
ORDER BY product_type, gwp_crore DESC;

-- QUERY 2: Empirical Claim Frequency by Segment
SELECT
    p.product_type,
    p.region,
    COUNT(DISTINCT p.policy_id) AS exposed_policies,
    COUNT(c.claim_id) AS claim_count,
    ROUND(COUNT(c.claim_id) * 1.0 / COUNT(DISTINCT p.policy_id), 4) AS claim_frequency,
    CASE
      WHEN ABS(COUNT(c.claim_id) * 1.0 / COUNT(DISTINCT p.policy_id) - 0.01) > 0.002 THEN 'REVIEW'
      ELSE 'OK'
    END AS vs_model_assumption
FROM policies p
LEFT JOIN claims c ON p.policy_id = c.policy_id
WHERE p.status != 'Cancelled'
GROUP BY p.product_type, p.region
ORDER BY claim_frequency DESC;

-- QUERY 3: Severity Distribution by Claim Type
SELECT
    claim_type,
    COUNT(*) AS claim_count,
    ROUND(AVG(gross_loss), 0) AS mean_severity_rs,
    ROUND(MIN(gross_loss), 0) AS min_rs,
    ROUND(MAX(gross_loss), 0) AS max_rs,
    ROUND(SUM(gross_loss) / 1e7, 2) AS total_loss_crore,
    -- Note: Uses SQRT() for empirical CV. Requires SQLite build with math functions enabled.
    -- If unavailable, compute CV in Python from extracted claims data.
    ROUND(
        SQRT(AVG(gross_loss * gross_loss) - AVG(gross_loss) * AVG(gross_loss))/ AVG(gross_loss),3
    ) AS empirical_cv,
    ROUND(SUM(paid_loss) / SUM(gross_loss), 3) AS paid_to_incurred
FROM claims
GROUP BY claim_type
ORDER BY mean_severity_rs DESC;

-- Assumption:
-- Synthetic dataset allows at most one claim per policy.
-- Therefore SUM(p.annual_premium) is not duplicated by the LEFT JOIN.
-- For real multi-claim datasets, premium should be aggregated separately.
-- QUERY 4: Loss Ratio Analysis by Product Type
-- Note:
-- Claims represent full-year simulated losses.
-- Therefore annual premium is used as denominator for consistency with the synthetic portfolio design assumptions.
-- In a real actuarial setting, earned premium would be the correct denominator. Using annual premium here materially understates loss ratio because average exposure is approximately 58.6% of a full policy year.

SELECT
    p.product_type,
    ROUND(SUM(p.annual_premium) / 1e7, 2) AS annual_premium_crore,
    ROUND(SUM(c.gross_loss) / 1e7, 2) AS incurred_loss_crore,
    ROUND(SUM(c.gross_loss) / SUM(p.annual_premium), 4) AS loss_ratio,
    0.30 AS expense_ratio,
    0.08 AS ri_cost_ratio,
    ROUND(SUM(c.gross_loss) / SUM(p.annual_premium) + 0.30 + 0.08, 4) AS combined_ratio,
    CASE
      WHEN SUM(c.gross_loss) / SUM(p.annual_premium) + 0.38 > 1.0 THEN 'UNPROFITABLE'
      ELSE 'Profitable'
    END AS profitability_flag
FROM policies p
LEFT JOIN claims c ON p.policy_id = c.policy_id
GROUP BY p.product_type
ORDER BY combined_ratio DESC;

-- QUERY 5: Reinsurance Recovery Analysis (XL ONLY)
-- Note:
-- Current actuarial model applies only the XL per-risk treaty.
-- Quota share and stop-loss treaties exist in the database for future extension,
-- but are intentionally excluded from current stochastic loss modelling.
SELECT
    c.claim_id,
    p.product_type,
    p.region,
    ROUND(c.gross_loss, 0) AS gross_loss_rs,
    ROUND(MIN(c.gross_loss, 500000), 0) AS insurer_retention_rs,
    ROUND(MAX(0, MIN(c.gross_loss - 500000, 4500000)), 0) AS ri_recovery_rs,
    c.claim_type,
    c.status
FROM claims c
JOIN policies p ON c.policy_id = p.policy_id
WHERE c.gross_loss > 500000
ORDER BY c.gross_loss DESC;

SELECT
    COUNT(*) AS xl_claims_count,
    ROUND(SUM(gross_loss) / 1e7, 2) AS total_gross_loss_crore,
    ROUND(SUM(MIN(gross_loss, 500000)) / 1e7, 2) AS total_retention_crore,
    ROUND(SUM(MAX(0, MIN(gross_loss - 500000, 4500000))) / 1e7, 2) AS total_ri_recovery_crore,
    ROUND(SUM(MAX(0, MIN(gross_loss - 500000, 4500000))) / NULLIF(SUM(gross_loss), 0) * 100, 1) AS ri_recovery_pct_of_gross
FROM claims
WHERE gross_loss > 500000;

-- QUERY 6: Large Loss Report — Top 20 Claims
SELECT
    ROW_NUMBER() OVER (ORDER BY c.gross_loss DESC) AS rank,
    c.claim_id,
    c.policy_id,
    p.product_type,
    p.region,
    c.claim_date,
    c.claim_type,
    ROUND(c.gross_loss, 0) AS gross_loss_rs,
    ROUND(MIN(c.gross_loss, 500000), 0) AS net_retention_rs,
    ROUND(MAX(0, MIN(c.gross_loss - 500000, 4500000)), 0) AS ri_recovery_rs,
    c.status
FROM claims c
JOIN policies p ON c.policy_id = p.policy_id
ORDER BY c.gross_loss DESC
LIMIT 20;

-- QUERY 7: Underwriting Year Development
SELECT
    uw_year,
    product_type,
    policies_written,
    ROUND(gwp / 1e7, 2) AS gwp_crore,
    ROUND(earned_premium / 1e7, 2) AS earned_crore,
    reported_claims,
    ROUND(incurred_loss / 1e7, 2) AS incurred_crore,
    ROUND(paid_loss / 1e7, 2) AS paid_crore,
    ROUND(ibnr_estimate / 1e7, 2) AS ibnr_crore,
    ROUND(loss_ratio * 100, 1) AS loss_ratio_pct,
    ROUND(combined_ratio * 100, 1) AS combined_ratio_pct,
    ROUND(paid_loss / NULLIF(incurred_loss, 0), 3) AS paid_to_incurred,
    CASE
        WHEN paid_loss / NULLIF(incurred_loss, 0) >= 0.90 THEN 'Mature'
        WHEN paid_loss / NULLIF(incurred_loss, 0) >= 0.70 THEN 'Developing'
        ELSE 'Early'
    END AS development_stage
FROM underwriting_years
ORDER BY uw_year DESC, product_type;

-- QUERY 8: Model Input Extraction — The Pipeline Query
SELECT
    COUNT(DISTINCT p.policy_id) AS num_policies,
    ROUND(SUM(p.annual_premium), 0) AS gross_written_premium_rs,
    ROUND(SUM(p.earned_premium) / COUNT(DISTINCT p.policy_id), 0) AS avg_premium_per_policy,
    ROUND(COUNT(c.claim_id) * 1.0 / (SELECT COUNT(*) FROM policies WHERE status != 'Cancelled'), 4) AS empirical_claim_frequency,
    ROUND(AVG(c.gross_loss), 0) AS empirical_mean_severity_rs,
    ROUND(SUM(c.gross_loss) / SUM(p.annual_premium), 4) AS empirical_loss_ratio,
    ROUND((COUNT(c.claim_id) * 1.0 / COUNT(DISTINCT p.policy_id) - 0.01) / 0.01 * 100, 2) AS frequency_deviation_pct,
    ROUND((AVG(c.gross_loss) - 120000) / 120000 * 100, 2) AS severity_deviation_pct,
    ROUND((SUM(c.gross_loss) / SUM(p.earned_premium) - 0.60) / 0.60 * 100, 2) AS loss_ratio_deviation_pct
FROM policies p
LEFT JOIN claims c ON p.policy_id = c.policy_id
;