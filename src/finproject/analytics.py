from __future__ import annotations

from dataclasses import asdict
import csv
from pathlib import Path
from statistics import mean, pstdev
from typing import TYPE_CHECKING

from .synthetic_data import MarketRow

if TYPE_CHECKING:
    from .backtest import EquityCurvePoint


def _pct_change(values: list[float]) -> list[float | None]:
    out: list[float | None] = [None]
    for i in range(1, len(values)):
        prev = values[i - 1]
        out.append((values[i] / prev) - 1.0)
    return out


def _rolling(values: list[float], window: int, fn) -> list[float | None]:
    out: list[float | None] = []
    for idx in range(len(values)):
        if idx + 1 < window:
            out.append(None)
            continue
        win = values[idx + 1 - window : idx + 1]
        out.append(fn(win))
    return out


def _rolling_drawdown(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    for idx in range(len(values)):
        if idx + 1 < window:
            out.append(None)
            continue
        win = values[idx + 1 - window : idx + 1]
        peak = max(win)
        out.append((values[idx] / peak) - 1.0)
    return out


def build_feature_frame(rows: list[MarketRow]) -> list[dict[str, float | str | None]]:
    """Compute finance features that are common in risk/regime systems."""
    prices = [r.price for r in rows]
    returns = _pct_change(prices)
    clean_returns = [0.0 if x is None else x for x in returns]

    mom_20 = _rolling(prices, 20, lambda x: (x[-1] / x[0]) - 1.0)
    vol_20 = _rolling(clean_returns, 20, lambda x: pstdev(x))
    drawdown_60 = _rolling_drawdown(prices, 60)
    trend_50 = _rolling(prices, 50, mean)

    frame: list[dict[str, float | str | None]] = []
    for idx, row in enumerate(rows):
        trend = trend_50[idx]
        price_vs_trend = None if trend is None else (row.price / trend) - 1.0

        frame.append(
            {
                "day": row.day.isoformat(),
                "price": row.price,
                "benchmark": row.benchmark,
                "return_1d": returns[idx],
                "momentum_20": mom_20[idx],
                "volatility_20": vol_20[idx],
                "drawdown_60": drawdown_60[idx],
                "price_vs_ma50": price_vs_trend,
                "vix": row.vix,
                "rate_10y": row.rate_10y,
            }
        )
    return frame


def export_rows_csv(rows: list[MarketRow], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["day", "price", "benchmark", "vix", "rate_10y"])
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row) | {"day": row.day.isoformat()})


def export_features_csv(frame: list[dict[str, float | str | None]], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(frame[0].keys()) if frame else []
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(frame)


def export_equity_curve_csv(curve: list[EquityCurvePoint], output_file: Path) -> None:
    """Export day-by-day strategy vs benchmark equity curve for charting."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["day", "strategy_equity", "benchmark_equity", "strategy_drawdown", "benchmark_drawdown", "regime"]
    with output_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for point in curve:
            writer.writerow({
                "day": point.day,
                "strategy_equity": point.strategy_equity,
                "benchmark_equity": point.benchmark_equity,
                "strategy_drawdown": point.strategy_drawdown,
                "benchmark_drawdown": point.benchmark_drawdown,
                "regime": point.regime,
            })


