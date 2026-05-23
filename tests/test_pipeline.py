from __future__ import annotations

import sys
from pathlib import Path
import importlib
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

analytics = importlib.import_module("finproject.analytics")
regime = importlib.import_module("finproject.regime")
service = importlib.import_module("finproject.service")
synthetic_data = importlib.import_module("finproject.synthetic_data")
backtest = importlib.import_module("finproject.backtest")

build_feature_frame = analytics.build_feature_frame
build_portfolio_tilts = regime.build_portfolio_tilts
classify_regimes = regime.classify_regimes
build_snapshot = service.build_snapshot
generate_market_data = synthetic_data.generate_market_data
run_regime_backtest = backtest.run_regime_backtest


class PipelineTests(unittest.TestCase):
    def test_feature_frame_keeps_length(self) -> None:
        rows = generate_market_data(days=250, seed=11)
        features = build_feature_frame(rows)
        self.assertEqual(len(rows), len(features))
        self.assertIn("momentum_20", features[-1])

    def test_regime_output_has_multiple_states(self) -> None:
        rows = generate_market_data(days=500, seed=11)
        features = build_feature_frame(rows)
        regimes = classify_regimes(features)
        labels = {r.regime for r in regimes}
        self.assertGreaterEqual(len(labels), 2)

    def test_tilt_weights_sum_to_one(self) -> None:
        rows = generate_market_data(days=350, seed=5)
        features = build_feature_frame(rows)
        regimes = classify_regimes(features)
        tilts = build_portfolio_tilts(regimes)

        total = tilts[-1]["equity"] + tilts[-1]["bonds"] + tilts[-1]["cash"]
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_snapshot_shape(self) -> None:
        snapshot = build_snapshot(days=120, seed=9)
        self.assertIn("latest", snapshot)
        self.assertIn("regimes", snapshot)
        self.assertIn("tilts", snapshot)
        self.assertIn("backtest", snapshot)
        self.assertIn("meta", snapshot)
        self.assertIn("regime", snapshot["latest"])

    def test_backtest_metrics_in_range(self) -> None:
        rows = generate_market_data(days=300, seed=9)
        features = build_feature_frame(rows)
        regimes = classify_regimes(features)
        tilts = build_portfolio_tilts(regimes)
        report = run_regime_backtest(features, tilts)

        self.assertGreaterEqual(report.annualized_volatility, 0.0)
        self.assertLessEqual(report.max_drawdown, 0.0)


if __name__ == "__main__":
    unittest.main()

