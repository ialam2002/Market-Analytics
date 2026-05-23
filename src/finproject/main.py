from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analytics import build_feature_frame, export_equity_curve_csv, export_features_csv, export_rows_csv
from .backtest import run_regime_backtest
from .data_sources import load_market_data
from .regime import build_portfolio_tilts, classify_regimes
from .service import run_server


def run_build(days: int, seed: int, out_dir: Path, data_source: str, csv_file: Path | None) -> None:
    loaded = load_market_data(source=data_source, days=days, seed=seed, csv_file=csv_file)
    rows = loaded.rows
    frame = build_feature_frame(rows)
    regimes = classify_regimes(frame)
    tilts = build_portfolio_tilts(regimes)
    result = run_regime_backtest(frame, tilts)
    backtest = result.report

    out_dir.mkdir(parents=True, exist_ok=True)
    export_rows_csv(rows, out_dir / "market_data.csv")
    export_features_csv(frame, out_dir / "feature_frame.csv")
    export_equity_curve_csv(result.equity_curve, out_dir / "equity_curve.csv")

    report = {
        "data_source": loaded.source_used,
        "data_note": loaded.note,
        "latest_regime": regimes[-1].__dict__,
        "latest_tilt": tilts[-1],
        "backtest": backtest.__dict__,
        "regime_counts": {
            "RISK_ON": sum(1 for r in regimes if r.regime == "RISK_ON"),
            "TRANSITION": sum(1 for r in regimes if r.regime == "TRANSITION"),
            "RISK_OFF": sum(1 for r in regimes if r.regime == "RISK_OFF"),
        },
    }

    with (out_dir / "regime_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print(f"Artifacts created in: {out_dir}")
    print(json.dumps(report, indent=2))


def run_demo(days: int, seed: int, data_source: str, csv_file: Path | None) -> None:
    loaded = load_market_data(source=data_source, days=days, seed=seed, csv_file=csv_file)
    rows = loaded.rows
    frame = build_feature_frame(rows)
    regimes = classify_regimes(frame)
    tilts = build_portfolio_tilts(regimes)
    result = run_regime_backtest(frame, tilts)
    bt = result.report

    print("Data source:", loaded.source_used)
    print("Data note:", loaded.note)
    print("Latest day:", frame[-1]["day"])
    print("Regime:", regimes[-1].regime)
    print("Confidence:", regimes[-1].confidence)
    print("Recommended tilt:", tilts[-1])
    print()
    print("── Strategy ──────────────────────────")
    print(f"  CAGR:             {bt.cagr:+.2%}")
    print(f"  Sharpe:           {bt.sharpe:.3f}")
    print(f"  Max Drawdown:     {bt.max_drawdown:.2%}")
    print(f"  Ann. Volatility:  {bt.annualized_volatility:.2%}")
    print()
    print("── Benchmark ─────────────────────────")
    print(f"  CAGR:             {bt.benchmark_cagr:+.2%}")
    print(f"  Sharpe:           {bt.benchmark_sharpe:.3f}")
    print(f"  Max Drawdown:     {bt.benchmark_max_drawdown:.2%}")
    print()
    print("── Relative ──────────────────────────")
    print(f"  Alpha:            {bt.alpha:+.4f}")
    print(f"  Beta:             {bt.beta:.4f}")
    print(f"  Info Ratio:       {bt.information_ratio:.4f}")
    print(f"  Excess Return:    {bt.excess_return:+.2%}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Market regime analytics portfolio project")

    sub = parser.add_subparsers(dest="command", required=True)

    def add_common_options(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--days", type=int, default=756)
        command_parser.add_argument("--seed", type=int, default=7)
        command_parser.add_argument(
            "--data-source",
            choices=["synthetic", "csv", "live"],
            default="synthetic",
            help="Data source for market rows",
        )
        command_parser.add_argument(
            "--csv-file",
            type=Path,
            default=None,
            help="Path to CSV containing day,price,benchmark,vix,rate_10y",
        )

    demo = sub.add_parser("demo", help="Print latest regime and allocation")
    add_common_options(demo)

    build = sub.add_parser("build", help="Export data artifacts as CSV/JSON")
    add_common_options(build)
    build.add_argument("--out-dir", type=Path, default=Path("artifacts"))

    api = sub.add_parser("api", help="Run API and dashboard server")
    add_common_options(api)
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8000)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "demo":
        run_demo(days=args.days, seed=args.seed, data_source=args.data_source, csv_file=args.csv_file)
    elif args.command == "build":
        run_build(
            days=args.days,
            seed=args.seed,
            out_dir=args.out_dir,
            data_source=args.data_source,
            csv_file=args.csv_file,
        )
    elif args.command == "api":
        run_server(
            host=args.host,
            port=args.port,
            days=args.days,
            seed=args.seed,
            data_source=args.data_source,
            csv_file=args.csv_file,
        )
    else:
        parser.error("Unknown command")


if __name__ == "__main__":
    main()

