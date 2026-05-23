# Market Regime Analytics

[![CI](https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO/actions/workflows/ci.yml)

> Replace `YOUR_GITHUB_USERNAME/YOUR_REPO` in the badge URL with your actual GitHub path.

A Python project that ingests market and macro data, detects risk regimes, backtests a regime-driven tactical allocation strategy, and serves the results through a local REST API and dashboard.

---

## How it works

```
Market data (Stooq / FRED / CSV / synthetic fallback)
        │
        ▼
  Feature pipeline   ──  20-day momentum, 20-day volatility, 60-day drawdown, price-vs-MA50
        │
        ▼
  Regime classifier  ──  RISK_ON / TRANSITION / RISK_OFF  (rule-based, interpretable)
        │
        ▼
  Backtest engine    ──  daily P&L, transaction costs, alpha/beta vs benchmark
        │
        ▼
  REST API           ──  regime signals, backtest report, equity curve
  Dashboard          ──  live metric cards, equity curve chart, drawdown comparison
```

The regime model is intentionally rule-based rather than statistical — it's easier to explain, audit,
and reason about in a risk context. The backtest uses the prior day's regime to set today's weights,
which avoids any forward-looking information.

---

## Project layout

```
src/finproject/
    synthetic_data.py   data generation with volatility regime cycles
    data_sources.py     multi-source loader (synthetic / CSV / live public feeds)
    analytics.py        feature engineering and CSV export
    regime.py           regime classification and portfolio weight mapping
    backtest.py         performance analytics vs benchmark (alpha, beta, IR, MDD...)
    service.py          HTTP server, REST API, and dashboard
    main.py             CLI entry points
run.py                  convenience launcher (no install required)
tests/
    test_pipeline.py
    test_data_sources.py
.github/workflows/ci.yml
```

---

## Quickstart

```powershell
# Show current regime and backtest summary
.\.venv\Scripts\python.exe .\run.py demo

# Export all artifacts to the artifacts/ folder
.\.venv\Scripts\python.exe .\run.py build --days 756 --out-dir artifacts

# Start the API and open the dashboard
.\.venv\Scripts\python.exe .\run.py api --port 8000
```

Then open `http://127.0.0.1:8000`.

---

## Data sources

Pass `--data-source` to any command. The three modes are:

| Mode | Behaviour |
|---|---|
| `synthetic` | Deterministic generated data — default, no network needed |
| `csv` | Load your own CSV with columns `day,price,benchmark,vix,rate_10y` |
| `live` | Fetch from Stooq (SPY, SPX) and FRED (VIXCLS, DGS10); falls back to synthetic on failure |

```powershell
.\.venv\Scripts\python.exe .\run.py demo --data-source live --days 500
.\.venv\Scripts\python.exe .\run.py demo --data-source csv --csv-file .\artifacts\market_data.csv
```

---

## Build artifacts

Running `build` writes four files:

| File | Contents |
|---|---|
| `market_data.csv` | Raw price, benchmark, VIX, and 10Y rate |
| `feature_frame.csv` | Engineered features for every trading day |
| `equity_curve.csv` | Daily strategy and benchmark equity, drawdowns, and regime label |
| `regime_report.json` | Summary JSON including full backtest metrics |

---

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /api/health` | Liveness check |
| `GET /api/latest` | Most recent regime, tilt, and feature values |
| `GET /api/backtest` | Full report: CAGR, Sharpe, MDD, alpha, beta, IR |
| `GET /api/equity-curve` | Day-by-day equity curve for both strategy and benchmark |
| `GET /api/regimes?limit=N` | Recent N regime observations |
| `GET /api/tilts?limit=N` | Recent N allocation snapshots |
| `GET /api/meta` | Data source and row count info |

---

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

Eight tests covering the feature pipeline, regime classification, backtest metrics, equity curve
structure, CSV loading, and the live-feed fallback path.

---

## Future work

- Rolling alpha/beta and benchmark-relative charts in the dashboard
- Docker image and cloud deployment (Railway/Fly.io)
- Persistent storage and scheduled ingestion so live data accumulates over time
- HMM-based regime detection as an alternative model for comparison

