# Market Regime Analytics Portfolio Project

[![CI](https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO/actions/workflows/ci.yml)

A recruiter-friendly finance + analytics + software engineering project.

This app ingests market and macro data (synthetic, CSV, or public live feeds), computes finance features, classifies market regimes, backtests tactical allocations, and serves results through a local API and dashboard.

## Why this helps with jobs

- Demonstrates finance domain logic: momentum, volatility, drawdown, risk regimes, tactical portfolio tilts.
- Demonstrates data engineering workflow: multi-source ingestion (synthetic/CSV/live), feature pipeline, artifact export.
- Demonstrates software engineering: package structure, CLI, API server, backtest engine, tests, CI workflow, and documentation.
- Gives easy talking points for interviews: architecture choices, model interpretability, and production-readiness roadmap.

## Project structure

- `src/finproject/synthetic_data.py` - synthetic market + macro data generator.
- `src/finproject/data_sources.py` - synthetic/CSV/live source adapters with fallback logic.
- `src/finproject/analytics.py` - feature engineering and CSV export.
- `src/finproject/regime.py` - regime classifier and allocation mapping.
- `src/finproject/backtest.py` - tactical strategy backtest and performance metrics.
- `src/finproject/service.py` - HTTP API and minimal dashboard.
- `src/finproject/main.py` - CLI entry points.
- `run.py` - convenient launcher.
- `tests/test_pipeline.py` and `tests/test_data_sources.py` - test harness.
- `.github/workflows/ci.yml` - automated tests for pushes and pull requests.

## Quick start

```powershell
.\.venv\Scripts\python.exe .\run.py demo
```

## Data source modes

Use one of `synthetic`, `csv`, or `live` on every command via `--data-source`.

- `synthetic`: deterministic generated data.
- `csv`: load your own historical rows from a CSV with columns `day,price,benchmark,vix,rate_10y`.
- `live`: try public Stooq/FRED feeds; automatically falls back to synthetic if unavailable.

Examples:

```powershell
.\.venv\Scripts\python.exe .\run.py demo --data-source live --days 500
.\.venv\Scripts\python.exe .\run.py demo --data-source csv --csv-file .\artifacts\market_data.csv --days 200
```

## Export data artifacts

```powershell
.\.venv\Scripts\python.exe .\run.py build --days 756 --out-dir artifacts --data-source live
```

Creates:

- `artifacts/market_data.csv`
- `artifacts/feature_frame.csv`
- `artifacts/regime_report.json`

The JSON report now includes backtest metrics (`CAGR`, `Sharpe`, `Max Drawdown`, turnover, and transaction-cost impact).

## Run API and dashboard

```powershell
.\.venv\Scripts\python.exe .\run.py api --host 127.0.0.1 --port 8000 --data-source live
```

Then open: `http://127.0.0.1:8000`

API endpoints:

- `GET /api/health`
- `GET /api/latest`
- `GET /api/backtest`
- `GET /api/regimes?limit=12`
- `GET /api/tilts?limit=12`
- `GET /api/meta`

## Run tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

## Resume bullets (copy-ready)

- Built an end-to-end market regime analytics platform combining data ingestion, feature engineering, interpretable risk-state modeling, and tactical allocation recommendations.
- Implemented multi-source market data adapters (synthetic, CSV, and public live feeds) with graceful fallback logic for reproducible local demos.
- Developed a regime-driven backtest engine with transaction costs and performance analytics (CAGR, Sharpe, volatility, max drawdown, turnover).
- Designed and shipped a Python API + dashboard exposing live regime signals, backtest metrics, and portfolio tilt recommendations.
- Added automated CI with GitHub Actions and a reproducible unit test suite to validate core analytics and data-loading paths.

## Stretch upgrades (next)

1. Add benchmark relative metrics and rolling alpha/beta in the backtest report.
2. Add Docker support and deploy API to cloud.
3. Add frontend charting library for richer dashboards.
4. Add scheduled ingestion and persistent storage.

