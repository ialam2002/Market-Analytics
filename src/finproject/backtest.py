from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class BacktestReport:
    start_day: str
    end_day: str
    total_return: float
    cagr: float
    annualized_volatility: float
    sharpe: float
    max_drawdown: float
    turnover: float
    transaction_cost_impact: float


def _pct_change(values: list[float]) -> list[float]:
    out: list[float] = [0.0]
    for idx in range(1, len(values)):
        out.append((values[idx] / values[idx - 1]) - 1.0)
    return out


def _max_drawdown(returns: list[float]) -> float:
    equity = 1.0
    peak = 1.0
    max_dd = 0.0

    for ret in returns:
        equity *= 1.0 + ret
        peak = max(peak, equity)
        drawdown = (equity / peak) - 1.0
        max_dd = min(max_dd, drawdown)

    return max_dd


def run_regime_backtest(
    feature_frame: list[dict[str, float | str | None]],
    tilts: list[dict[str, float | str]],
    transaction_cost_bps: float = 5.0,
) -> BacktestReport:
    """Backtest tactical weights based on prior-day regime to avoid lookahead bias."""
    if len(feature_frame) < 3:
        raise ValueError("Need at least 3 rows for backtest")

    benchmark_levels = [float(row["benchmark"]) for row in feature_frame]
    benchmark_returns = _pct_change(benchmark_levels)

    strategy_returns: list[float] = [0.0]
    total_turnover = 0.0
    total_cost = 0.0

    prev_tilt = {
        "equity": float(tilts[0]["equity"]),
        "bonds": float(tilts[0]["bonds"]),
        "cash": float(tilts[0]["cash"]),
    }

    for idx in range(1, len(feature_frame)):
        today = feature_frame[idx]
        yesterday = feature_frame[idx - 1]

        eq_ret = float(today["return_1d"] or 0.0)
        rate_today = float(today["rate_10y"])
        rate_yesterday = float(yesterday["rate_10y"])

        # Approximate long-duration bond ETF returns from rate move.
        bond_ret = -7.5 * (rate_today - rate_yesterday) / 100.0
        cash_ret = 0.00008

        traded_tilt = {
            "equity": float(tilts[idx - 1]["equity"]),
            "bonds": float(tilts[idx - 1]["bonds"]),
            "cash": float(tilts[idx - 1]["cash"]),
        }

        turnover = (
            abs(traded_tilt["equity"] - prev_tilt["equity"])
            + abs(traded_tilt["bonds"] - prev_tilt["bonds"])
            + abs(traded_tilt["cash"] - prev_tilt["cash"])
        )
        cost = turnover * (transaction_cost_bps / 10_000.0)

        port_ret = (
            traded_tilt["equity"] * eq_ret
            + traded_tilt["bonds"] * bond_ret
            + traded_tilt["cash"] * cash_ret
            - cost
        )

        strategy_returns.append(port_ret)
        total_turnover += turnover
        total_cost += cost
        prev_tilt = traded_tilt

    n = len(strategy_returns)
    total_return = math.prod(1.0 + r for r in strategy_returns) - 1.0

    years = max(1.0 / 252.0, n / 252.0)
    cagr = (1.0 + total_return) ** (1.0 / years) - 1.0

    mean_ret = sum(strategy_returns) / n
    variance = sum((r - mean_ret) ** 2 for r in strategy_returns) / n
    ann_vol = float(math.sqrt(variance) * math.sqrt(252.0))

    excess_ret = mean_ret - 0.00008
    sharpe = 0.0 if ann_vol == 0 else (excess_ret * 252.0) / ann_vol

    _ = benchmark_returns  # keep available for future benchmark comparison extension.

    return BacktestReport(
        start_day=str(feature_frame[0]["day"]),
        end_day=str(feature_frame[-1]["day"]),
        total_return=round(total_return, 6),
        cagr=round(cagr, 6),
        annualized_volatility=round(float(ann_vol), 6),
        sharpe=round(sharpe, 6),
        max_drawdown=round(_max_drawdown(strategy_returns), 6),
        turnover=round(total_turnover, 6),
        transaction_cost_impact=round(total_cost, 6),
    )

