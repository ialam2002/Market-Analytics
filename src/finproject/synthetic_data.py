from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import random


@dataclass(frozen=True)
class MarketRow:
    day: date
    price: float
    benchmark: float
    vix: float
    rate_10y: float


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def generate_market_data(days: int = 756, seed: int = 7) -> list[MarketRow]:
    """Generate synthetic market + macro time-series for demo and testing."""
    rng = random.Random(seed)
    today = date.today()

    price = 100.0
    benchmark = 100.0
    vix = 18.0
    rate = 3.6
    rows: list[MarketRow] = []

    for idx in range(days):
        day = today - timedelta(days=(days - idx - 1))

        # Alternate volatility regimes every ~4 months to create realistic cycles.
        phase = (idx // 80) % 3
        if phase == 0:
            drift, vol = 0.0006, 0.009
        elif phase == 1:
            drift, vol = -0.0001, 0.017
        else:
            drift, vol = 0.0003, 0.012

        shock = rng.gauss(0.0, vol)
        benchmark_shock = 0.85 * shock + rng.gauss(0.0, vol * 0.5)

        price = max(20.0, price * (1.0 + drift + shock))
        benchmark = max(20.0, benchmark * (1.0 + 0.0004 + benchmark_shock))

        vix += 0.15 * (20.0 - vix) + rng.gauss(0.0, 1.35)
        vix = _clamp(vix, 10.0, 55.0)

        rate += 0.04 * (3.5 - rate) + rng.gauss(0.0, 0.06)
        rate = _clamp(rate, 0.8, 6.5)

        rows.append(
            MarketRow(
                day=day,
                price=round(price, 4),
                benchmark=round(benchmark, 4),
                vix=round(vix, 4),
                rate_10y=round(rate, 4),
            )
        )

    return rows

