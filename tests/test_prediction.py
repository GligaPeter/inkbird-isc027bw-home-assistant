"""Regression tests for built-in temperature prediction."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SOURCE = (
    Path(__file__).parents[1]
    / "custom_components"
    / "inkbird_ble"
    / "prediction.py"
)
SPEC = importlib.util.spec_from_file_location("inkbird_prediction", SOURCE)
assert SPEC is not None and SPEC.loader is not None
PREDICTION = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PREDICTION
SPEC.loader.exec_module(PREDICTION)


class PredictionTests(unittest.TestCase):
    def test_linear_regression_rate_per_minute(self) -> None:
        trend = PREDICTION.TemperatureTrend(
            1200, minimum_span_seconds=30, minimum_samples=5
        )
        for timestamp in range(0, 61, 10):
            trend.add(20 + timestamp / 30, timestamp)
        self.assertAlmostEqual(trend.rate_per_minute, 2.0, places=3)

    def test_window_discards_old_readings(self) -> None:
        trend = PREDICTION.TemperatureTrend(
            60, minimum_span_seconds=30, minimum_samples=3
        )
        trend.add(10, 0)
        trend.add(20, 30)
        trend.add(30, 60)
        trend.add(40, 90)
        self.assertAlmostEqual(trend.rate_per_minute, 20.0, places=3)

    def test_missing_probe_clears_history(self) -> None:
        trend = PREDICTION.TemperatureTrend(
            60, minimum_span_seconds=20, minimum_samples=3
        )
        trend.add(20, 0)
        trend.add(21, 10)
        trend.add(22, 20)
        self.assertIsNotNone(trend.rate_per_minute)
        trend.add(None, 30)
        self.assertIsNone(trend.rate_per_minute)

    def test_meat_eta_uses_exponential_heating_curve(self) -> None:
        minutes = PREDICTION.meat_eta_minutes(50, 120, 73, 1.4)
        self.assertIsNotNone(minutes)
        self.assertAlmostEqual(minutes, 20.0, delta=0.5)

    def test_eta_statuses(self) -> None:
        self.assertEqual(
            PREDICTION.eta_state(None, 73, 1, 120)[0], "Sensor not connected"
        )
        self.assertEqual(PREDICTION.eta_state(74, 73, 1, 120)[0], "Target reached")
        self.assertEqual(
            PREDICTION.eta_state(50, 73, None, 120)[0],
            "Collecting heating data",
        )


if __name__ == "__main__":
    unittest.main()
