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
        self.assertIn("equity_curve", snapshot)
        self.assertIn("regime", snapshot["latest"])
        # benchmark fields present
        self.assertIn("benchmark_cagr", snapshot["backtest"])
        self.assertIn("alpha", snapshot["backtest"])
        self.assertIn("information_ratio", snapshot["backtest"])

    def test_backtest_metrics_in_range(self) -> None:
        rows = generate_market_data(days=300, seed=9)
        features = build_feature_frame(rows)
        regimes = classify_regimes(features)
        tilts = build_portfolio_tilts(regimes)
        result = run_regime_backtest(features, tilts)
        report = result.report

        self.assertGreaterEqual(report.annualized_volatility, 0.0)
        self.assertLessEqual(report.max_drawdown, 0.0)
        self.assertGreaterEqual(report.benchmark_volatility, 0.0)
        self.assertLessEqual(report.benchmark_max_drawdown, 0.0)
        # beta should be a finite real number
        self.assertFalse(report.beta != report.beta)  # NaN check

    def test_equity_curve_structure(self) -> None:
        rows = generate_market_data(days=100, seed=3)
        features = build_feature_frame(rows)
        regimes = classify_regimes(features)
        tilts = build_portfolio_tilts(regimes)
        result = run_regime_backtest(features, tilts)

        self.assertEqual(len(result.equity_curve), len(features))
        point = result.equity_curve[-1]
        self.assertAlmostEqual(point.strategy_equity, 1.0 + result.report.total_return, places=3)
        self.assertIn(point.regime, {"RISK_ON", "TRANSITION", "RISK_OFF"})
        self.assertLessEqual(point.strategy_drawdown, 0.0001)  # drawdown ≤ 0 at all times


if __name__ == "__main__":
    unittest.main()

