from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class BacktestReport:
    # ── strategy ─────────────────────────────────────────────────────────
    start_day: str
    end_day: str
    total_return: float
    cagr: float
    annualized_volatility: float
    sharpe: float
    max_drawdown: float
    turnover: float
    transaction_cost_impact: float
    # ── benchmark ────────────────────────────────────────────────────────
    benchmark_total_return: float
    benchmark_cagr: float
    benchmark_volatility: float
    benchmark_sharpe: float
    benchmark_max_drawdown: float
    # ── relative metrics ─────────────────────────────────────────────────
    alpha: float           # annualised Jensen's alpha (strategy - beta*benchmark excess)
    beta: float            # market beta of strategy vs benchmark
    information_ratio: float  # active return / tracking error
    excess_return: float   # strategy_cagr - benchmark_cagr


@dataclass(frozen=True)
class EquityCurvePoint:
    day: str
    strategy_equity: float      # rebased to 1.0 at start
    benchmark_equity: float     # rebased to 1.0 at start
    strategy_drawdown: float    # running drawdown from peak
    benchmark_drawdown: float
    regime: str


@dataclass(frozen=True)
class BacktestResult:
    report: BacktestReport
    equity_curve: list[EquityCurvePoint]


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


def _drawdown_series(returns: list[float]) -> list[float]:
    equity = 1.0
    peak = 1.0
    out: list[float] = []
    for ret in returns:
        equity *= 1.0 + ret
        peak = max(peak, equity)
        out.append(round((equity / peak) - 1.0, 6))
    return out


def _equity_series(returns: list[float]) -> list[float]:
    equity = 1.0
    out: list[float] = []
    for ret in returns:
        equity *= 1.0 + ret
        out.append(round(equity, 6))
    return out


def _ann_stats(returns: list[float], risk_free_daily: float = 0.00008) -> tuple[float, float, float]:
    """Return (annualised_vol, annualised_sharpe, annualised_mean_excess)."""
    n = len(returns)
    if n == 0:
        return 0.0, 0.0, 0.0
    mean_r = sum(returns) / n
    variance = sum((r - mean_r) ** 2 for r in returns) / n
    ann_vol = float(math.sqrt(variance) * math.sqrt(252.0))
    excess = (mean_r - risk_free_daily) * 252.0
    sharpe = 0.0 if ann_vol == 0 else excess / ann_vol
    return ann_vol, sharpe, excess


def _beta_alpha(
    strategy_returns: list[float],
    benchmark_returns: list[float],
    risk_free_daily: float = 0.00008,
) -> tuple[float, float]:
    """OLS beta and annualised Jensen's alpha."""
    n = len(strategy_returns)
    if n < 2:
        return 1.0, 0.0

    s_excess = [r - risk_free_daily for r in strategy_returns]
    b_excess = [r - risk_free_daily for r in benchmark_returns]

    mean_b = sum(b_excess) / n
    cov = sum((s_excess[i] - sum(s_excess) / n) * (b_excess[i] - mean_b) for i in range(n)) / n
    var_b = sum((b - mean_b) ** 2 for b in b_excess) / n

    beta = 0.0 if var_b == 0 else cov / var_b
    ann_s_excess = (sum(s_excess) / n) * 252.0
    ann_b_excess = (sum(b_excess) / n) * 252.0
    alpha = ann_s_excess - beta * ann_b_excess
    return round(beta, 6), round(alpha, 6)


def _information_ratio(strategy_returns: list[float], benchmark_returns: list[float]) -> float:
    n = len(strategy_returns)
    if n < 2:
        return 0.0
    active = [s - b for s, b in zip(strategy_returns, benchmark_returns)]
    mean_active = sum(active) / n
    te_var = sum((a - mean_active) ** 2 for a in active) / n
    tracking_error = float(math.sqrt(te_var) * math.sqrt(252.0))
    return 0.0 if tracking_error == 0 else round((mean_active * 252.0) / tracking_error, 6)


def run_regime_backtest(
    feature_frame: list[dict[str, float | str | None]],
    tilts: list[dict[str, float | str]],
    transaction_cost_bps: float = 5.0,
) -> BacktestResult:
    """Backtest tactical weights; returns report + daily equity curve for charting."""
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

        # Approximate long-duration bond ETF return from rate move (modified duration ≈ 7.5).
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

    # ── strategy metrics ──────────────────────────────────────────────────
    n = len(strategy_returns)
    total_return = math.prod(1.0 + r for r in strategy_returns) - 1.0
    years = max(1.0 / 252.0, n / 252.0)
    cagr = (1.0 + total_return) ** (1.0 / years) - 1.0

    ann_vol, sharpe, _ = _ann_stats(strategy_returns)

    # ── benchmark metrics ─────────────────────────────────────────────────
    bm_total_return = math.prod(1.0 + r for r in benchmark_returns) - 1.0
    bm_cagr = (1.0 + bm_total_return) ** (1.0 / years) - 1.0
    bm_ann_vol, bm_sharpe, _ = _ann_stats(benchmark_returns)

    # ── relative metrics ──────────────────────────────────────────────────
    beta, alpha = _beta_alpha(strategy_returns, benchmark_returns)
    ir = _information_ratio(strategy_returns, benchmark_returns)

    # ── equity curve ──────────────────────────────────────────────────────
    s_equity = _equity_series(strategy_returns)
    b_equity = _equity_series(benchmark_returns)
    s_drawdown = _drawdown_series(strategy_returns)
    b_drawdown = _drawdown_series(benchmark_returns)

    curve: list[EquityCurvePoint] = [
        EquityCurvePoint(
            day=str(feature_frame[idx]["day"]),
            strategy_equity=s_equity[idx],
            benchmark_equity=b_equity[idx],
            strategy_drawdown=s_drawdown[idx],
            benchmark_drawdown=b_drawdown[idx],
            regime=str(tilts[idx]["regime"]),
        )
        for idx in range(n)
    ]

    report = BacktestReport(
        start_day=str(feature_frame[0]["day"]),
        end_day=str(feature_frame[-1]["day"]),
        total_return=round(total_return, 6),
        cagr=round(cagr, 6),
        annualized_volatility=round(float(ann_vol), 6),
        sharpe=round(sharpe, 6),
        max_drawdown=round(_max_drawdown(strategy_returns), 6),
        turnover=round(total_turnover, 6),
        transaction_cost_impact=round(total_cost, 6),
        benchmark_total_return=round(bm_total_return, 6),
        benchmark_cagr=round(bm_cagr, 6),
        benchmark_volatility=round(float(bm_ann_vol), 6),
        benchmark_sharpe=round(bm_sharpe, 6),
        benchmark_max_drawdown=round(_max_drawdown(benchmark_returns), 6),
        alpha=alpha,
        beta=beta,
        information_ratio=ir,
        excess_return=round(cagr - bm_cagr, 6),
    )

    return BacktestResult(report=report, equity_curve=curve)

