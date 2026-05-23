from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analytics import build_feature_frame, export_features_csv, export_rows_csv
from .regime import build_portfolio_tilts, classify_regimes
from .service import run_server
from .synthetic_data import generate_market_data


def run_build(days: int, seed: int, out_dir: Path) -> None:
    rows = generate_market_data(days=days, seed=seed)
    frame = build_feature_frame(rows)
    regimes = classify_regimes(frame)
    tilts = build_portfolio_tilts(regimes)

    out_dir.mkdir(parents=True, exist_ok=True)
    export_rows_csv(rows, out_dir / "market_data.csv")
    export_features_csv(frame, out_dir / "feature_frame.csv")

    report = {
        "latest_regime": regimes[-1].__dict__,
        "latest_tilt": tilts[-1],
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


def run_demo(days: int, seed: int) -> None:
    rows = generate_market_data(days=days, seed=seed)
    frame = build_feature_frame(rows)
    regimes = classify_regimes(frame)
    tilts = build_portfolio_tilts(regimes)

    print("Latest day:", frame[-1]["day"])
    print("Regime:", regimes[-1].regime)
    print("Confidence:", regimes[-1].confidence)
    print("Recommended tilt:", tilts[-1])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Market regime analytics portfolio project")

    sub = parser.add_subparsers(dest="command", required=True)

    def add_common_options(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--days", type=int, default=756)
        command_parser.add_argument("--seed", type=int, default=7)

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
        run_demo(days=args.days, seed=args.seed)
    elif args.command == "build":
        run_build(days=args.days, seed=args.seed, out_dir=args.out_dir)
    elif args.command == "api":
        run_server(host=args.host, port=args.port, days=args.days, seed=args.seed)
    else:
        parser.error("Unknown command")


if __name__ == "__main__":
    main()

