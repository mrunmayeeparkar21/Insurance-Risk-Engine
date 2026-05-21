import sys
import os

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
sys.path.append(PROJECT_ROOT)

from phase2_python.insurance_risk_engine.stochastic_model import run_monte_carlo
from phase2_python.insurance_risk_engine.risk_metrics import compute_risk_metrics


def test_risk_metrics():
    losses, _ = run_monte_carlo()
    m = compute_risk_metrics(losses)

    # Expected annual loss sanity check
    expected_loss = 50_000 * 0.01 * 120_000
    assert abs(m["mean_loss"] - expected_loss) / expected_loss < 0.10

    # VaR ordering
    assert m["var_99_5"] > m["var_99"] > m["var_95"] > m["mean_loss"]

    # ES should exceed VaR
    assert m["es_99"] > m["var_99"]

    # SCR positive
    assert m["scr"] > 0

    # Solvency positive
    assert m["solvency_ratio"] > 0

    # Ruin probability bounds
    assert 0 <= m["ruin_probability"] <= 1

    print("All tests passed")


if __name__ == "__main__":
    test_risk_metrics()