# Market Regime Analytics Portfolio Project

A recruiter-friendly finance + analytics + software engineering project.

This app generates synthetic market data, computes finance features, classifies market regimes, and serves allocation recommendations through a local API and dashboard.

## Why this helps with jobs

- Demonstrates finance domain logic: momentum, volatility, drawdown, risk regimes, tactical portfolio tilts.
- Demonstrates data engineering workflow: reproducible synthetic ingestion, feature pipeline, artifact export.
- Demonstrates software engineering: package structure, CLI, API server, tests, and documentation.
- Gives easy talking points for interviews: architecture choices, model interpretability, and production-readiness roadmap.

## Project structure

- `src/finproject/synthetic_data.py` - synthetic market + macro data generator.
- `src/finproject/analytics.py` - feature engineering and CSV export.
- `src/finproject/regime.py` - regime classifier and allocation mapping.
- `src/finproject/service.py` - HTTP API and minimal dashboard.
- `src/finproject/main.py` - CLI entry points.
- `run.py` - convenient launcher.
- `tests/test_pipeline.py` - test harness.

## Quick start

```powershell
.\.venv\Scripts\python.exe .\run.py demo
```

## Export data artifacts

```powershell
.\.venv\Scripts\python.exe .\run.py build --days 756 --out-dir artifacts
```

Creates:

- `artifacts/market_data.csv`
- `artifacts/feature_frame.csv`
- `artifacts/regime_report.json`

## Run API and dashboard

```powershell
.\.venv\Scripts\python.exe .\run.py api --host 127.0.0.1 --port 8000
```

Then open: `http://127.0.0.1:8000`

API endpoints:

- `GET /api/health`
- `GET /api/latest`
- `GET /api/regimes?limit=12`
- `GET /api/tilts?limit=12`

## Run tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

## Stretch upgrades (next)

1. Replace synthetic data with live feeds (e.g., Stooq/FRED/Yahoo exports).
2. Add a backtest engine with transaction costs and benchmark comparisons.
3. Add CI (GitHub Actions) and code quality checks.
4. Add Docker support and deploy API to cloud.

