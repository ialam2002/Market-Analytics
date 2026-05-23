from __future__ import annotations

import csv
from datetime import date, timedelta
import importlib
import sys
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


data_sources = importlib.import_module("finproject.data_sources")
synthetic_data = importlib.import_module("finproject.synthetic_data")

load_market_data = data_sources.load_market_data
MarketRow = synthetic_data.MarketRow


class DataSourceTests(unittest.TestCase):
    def test_csv_source_reads_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_file = Path(tmp_dir) / "market.csv"
            start = date(2025, 1, 1)
            with csv_file.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["day", "price", "benchmark", "vix", "rate_10y"])
                writer.writeheader()
                for i in range(15):
                    writer.writerow(
                        {
                            "day": (start + timedelta(days=i)).isoformat(),
                            "price": 100 + i,
                            "benchmark": 200 + i,
                            "vix": 20 + (i % 3),
                            "rate_10y": 3.2 + (i * 0.01),
                        }
                    )

            loaded = load_market_data(source="csv", days=10, seed=3, csv_file=csv_file)
            self.assertEqual(loaded.source_used, "csv")
            self.assertEqual(len(loaded.rows), 10)
            self.assertEqual(loaded.rows[-1].price, 114.0)

    def test_live_loader_fallback(self) -> None:
        def broken_loader(_days: int) -> list[object]:
            raise TimeoutError("simulated")

        loaded = load_market_data(source="live", days=40, seed=12, live_loader=broken_loader)
        self.assertEqual(loaded.source_used, "synthetic-fallback")
        self.assertEqual(len(loaded.rows), 40)


if __name__ == "__main__":
    unittest.main()

