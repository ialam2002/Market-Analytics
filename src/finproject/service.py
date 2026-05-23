from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .analytics import build_feature_frame
from .backtest import run_regime_backtest
from .data_sources import load_market_data
from .regime import build_portfolio_tilts, classify_regimes


def build_snapshot(
    days: int = 756,
    seed: int = 7,
    data_source: str = "synthetic",
    csv_file: Path | None = None,
) -> dict[str, Any]:
    loaded = load_market_data(source=data_source, days=days, seed=seed, csv_file=csv_file)
    rows = loaded.rows
    features = build_feature_frame(rows)
    regimes = classify_regimes(features)
    tilts = build_portfolio_tilts(regimes)
    backtest = run_regime_backtest(features, tilts)

    return {
        "meta": {
            "source": loaded.source_used,
            "note": loaded.note,
            "rows": len(rows),
        },
        "features": features,
        "regimes": [r.__dict__ for r in regimes],
        "tilts": tilts,
        "backtest": backtest.__dict__,
        "latest": {
            "feature": features[-1],
            "regime": regimes[-1].__dict__,
            "tilt": tilts[-1],
        },
    }


def _dashboard_html() -> str:
    return """<!doctype html>
<html>
<head>
  <meta charset='utf-8'/>
  <title>Market Regime Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; background: #0b1220; color: #e7edf7; }
    .card { background: #141f35; border-radius: 10px; padding: 1rem; margin-bottom: 1rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; }
    h1 { margin-top: 0; }
    code { color: #8ec5ff; }
  </style>
</head>
<body>
  <h1>Market Regime Analytics</h1>
  <div class='grid'>
    <div class='card'><h3>Latest Regime</h3><div id='regime'>Loading...</div></div>
    <div class='card'><h3>Model Confidence</h3><div id='confidence'>Loading...</div></div>
    <div class='card'><h3>Portfolio Tilt</h3><div id='tilt'>Loading...</div></div>
    <div class='card'><h3>Backtest (CAGR / Sharpe)</h3><div id='backtest'>Loading...</div></div>
  </div>
  <div class='card'>
    <h3>Recent Regimes</h3>
    <pre id='history'>Loading...</pre>
  </div>
  <script>
    async function loadData() {
      const latest = await fetch('/api/latest').then(r => r.json());
      const history = await fetch('/api/regimes?limit=12').then(r => r.json());
      const backtest = await fetch('/api/backtest').then(r => r.json());

      document.getElementById('regime').textContent = latest.regime.regime;
      document.getElementById('confidence').textContent = (latest.regime.confidence * 100).toFixed(1) + '%';
      document.getElementById('tilt').textContent =
        'Equity ' + (latest.tilt.equity * 100).toFixed(0) + '% | ' +
        'Bonds ' + (latest.tilt.bonds * 100).toFixed(0) + '% | ' +
        'Cash ' + (latest.tilt.cash * 100).toFixed(0) + '%';
      document.getElementById('backtest').textContent =
        (backtest.cagr * 100).toFixed(2) + '% / ' + backtest.sharpe.toFixed(2);
      document.getElementById('history').textContent = JSON.stringify(history.items, null, 2);
    }
    loadData();
  </script>
</body>
</html>
"""


def create_handler(snapshot: dict[str, Any]) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _html(self, body: str, status: int = HTTPStatus.OK) -> None:
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)

            if parsed.path == "/":
                self._html(_dashboard_html())
                return

            if parsed.path == "/api/health":
                self._json({"status": "ok"})
                return

            if parsed.path == "/api/latest":
                self._json(snapshot["latest"])
                return

            if parsed.path == "/api/backtest":
                self._json(snapshot["backtest"])
                return

            if parsed.path == "/api/regimes":
                qs = parse_qs(parsed.query)
                limit = int(qs.get("limit", [20])[0])
                items = snapshot["regimes"][-max(1, limit) :]
                self._json({"items": items, "count": len(items)})
                return

            if parsed.path == "/api/tilts":
                qs = parse_qs(parsed.query)
                limit = int(qs.get("limit", [20])[0])
                items = snapshot["tilts"][-max(1, limit) :]
                self._json({"items": items, "count": len(items)})
                return

            if parsed.path == "/api/meta":
                self._json(snapshot["meta"])
                return

            self._json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    return Handler


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    days: int = 756,
    seed: int = 7,
    data_source: str = "synthetic",
    csv_file: Path | None = None,
) -> None:
    snapshot = build_snapshot(days=days, seed=seed, data_source=data_source, csv_file=csv_file)
    handler = create_handler(snapshot)
    server = ThreadingHTTPServer((host, port), handler)  # type: ignore[arg-type]
    print(f"Server running at http://{host}:{port}")
    print("API endpoints: /api/health, /api/latest, /api/backtest, /api/regimes, /api/tilts, /api/meta")
    server.serve_forever()

