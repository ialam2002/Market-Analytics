from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import random


@dataclass(frozen=True)
class MarketRow:
    """One calendar day of market and macro data.

    price and benchmark are total-return index levels rebased to 100 at the
    start of the series. vix is the CBOE VIX close. rate_10y is the US
    10-year Treasury yield in percent.
    """

    day: date
    price: float
    benchmark: float
    vix: float
    rate_10y: float


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def generate_market_data(days: int = 756, seed: int = 7) -> list[MarketRow]:
    """Return a reproducible list of synthetic daily market rows.

    The series simulates three repeating volatility regimes (bull, stress,
    recovery) that cycle roughly every 80 trading days. VIX and the 10-year
    rate both mean-revert: VIX to 20 and rates to 3.5%. Using a fixed seed
    produces identical output across runs, which keeps tests stable.
    """
    rng = random.Random(seed)
    today = date.today()

    price = 100.0
    benchmark = 100.0
    vix = 18.0
    rate = 3.6
    rows: list[MarketRow] = []

    for idx in range(days):
        day = today - timedelta(days=(days - idx - 1))

        # Three-phase cycle: low-vol bull (0), high-vol stress (1), recovery (2).
        phase = (idx // 80) % 3
        if phase == 0:
            drift, vol = 0.0006, 0.009
        elif phase == 1:
            drift, vol = -0.0001, 0.017
        else:
            drift, vol = 0.0003, 0.012

        shock = rng.gauss(0.0, vol)
        # Benchmark tracks the asset with some independent noise added.
        benchmark_shock = 0.85 * shock + rng.gauss(0.0, vol * 0.5)

        price = max(20.0, price * (1.0 + drift + shock))
        benchmark = max(20.0, benchmark * (1.0 + 0.0004 + benchmark_shock))

        # Mean-reversion: λ = 0.15 for VIX, λ = 0.04 for rates.
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
