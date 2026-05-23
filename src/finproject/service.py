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
    result = run_regime_backtest(features, tilts)

    return {
        "meta": {
            "source": loaded.source_used,
            "note": loaded.note,
            "rows": len(rows),
        },
        "features": features,
        "regimes": [r.__dict__ for r in regimes],
        "tilts": tilts,
        "backtest": result.report.__dict__,
        "equity_curve": [p.__dict__ for p in result.equity_curve],
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
    *, *::before, *::after { box-sizing: border-box; }
    body { font-family: Arial, sans-serif; margin: 0; padding: 1.5rem; background: #0b1220; color: #e7edf7; }
    h1 { margin: 0 0 1rem; font-size: 1.4rem; letter-spacing: .03em; }
    h3 { margin: 0 0 .5rem; font-size: .85rem; text-transform: uppercase; color: #8ec5ff; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: .8rem; margin-bottom: 1rem; }
    .card { background: #141f35; border-radius: 10px; padding: .9rem 1.1rem; }
    .val { font-size: 1.5rem; font-weight: bold; }
    .sub { font-size: .8rem; color: #8d9bb5; margin-top: .2rem; }
    .RISK_ON  { color: #4edc8a; }
    .RISK_OFF { color: #ff6b6b; }
    .TRANSITION { color: #f5c542; }
    canvas { width: 100%; height: 320px; display: block; }
    .chart-card { background: #141f35; border-radius: 10px; padding: 1rem; margin-bottom: 1rem; }
    .legend { display: flex; gap: 1.5rem; margin-top: .5rem; font-size: .8rem; }
    .legend span::before { content: ''; display: inline-block; width: 12px; height: 3px; border-radius: 2px; margin-right: 5px; vertical-align: middle; }
    .leg-s::before { background: #4edc8a; }
    .leg-b::before { background: #8ec5ff; }
    .metrics-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: .8rem; }
    @media (max-width: 600px) { .metrics-grid { grid-template-columns: 1fr 1fr; } }
    table { width: 100%; border-collapse: collapse; font-size: .82rem; }
    th { text-align: left; color: #8d9bb5; padding: .3rem .5rem; border-bottom: 1px solid #1e3050; }
    td { padding: .3rem .5rem; border-bottom: 1px solid #111d2e; }
  </style>
</head>
<body>
  <h1>&#x1F4C8; Market Regime Analytics Dashboard</h1>

  <div class='grid'>
    <div class='card'>
      <h3>Today's Regime</h3>
      <div class='val' id='regime'>…</div>
      <div class='sub'>Confidence: <span id='confidence'>…</span></div>
    </div>
    <div class='card'>
      <h3>Portfolio Tilt</h3>
      <div class='val' id='tilt-eq'>…</div>
      <div class='sub' id='tilt-rest'>…</div>
    </div>
    <div class='card'>
      <h3>Strategy CAGR</h3>
      <div class='val' id='s-cagr'>…</div>
      <div class='sub'>vs Benchmark: <span id='bm-cagr'>…</span></div>
    </div>
    <div class='card'>
      <h3>Sharpe / Alpha</h3>
      <div class='val' id='sharpe'>…</div>
      <div class='sub'>Alpha: <span id='alpha'>…</span> &nbsp; Beta: <span id='beta'>…</span></div>
    </div>
    <div class='card'>
      <h3>Max Drawdown</h3>
      <div class='val' id='mdd'>…</div>
      <div class='sub'>Benchmark: <span id='bm-mdd'>…</span></div>
    </div>
    <div class='card'>
      <h3>Info Ratio</h3>
      <div class='val' id='ir'>…</div>
      <div class='sub'>Excess Return: <span id='excess'>…</span></div>
    </div>
  </div>

  <div class='chart-card'>
    <h3>Equity Curve — Strategy vs Benchmark (rebased to 1.0)</h3>
    <canvas id='chart'></canvas>
    <div class='legend'>
      <span class='leg-s'>Strategy</span>
      <span class='leg-b'>Benchmark</span>
    </div>
  </div>

  <div class='chart-card'>
    <h3>Drawdown Comparison</h3>
    <canvas id='ddchart'></canvas>
    <div class='legend'>
      <span class='leg-s'>Strategy</span>
      <span class='leg-b'>Benchmark</span>
    </div>
  </div>

  <div class='card' style='margin-bottom:1rem'>
    <h3>Recent Regimes (last 15 days)</h3>
    <table>
      <thead><tr><th>Day</th><th>Regime</th><th>Confidence</th><th>Equity</th><th>Bonds</th><th>Cash</th></tr></thead>
      <tbody id='regime-table'></tbody>
    </table>
  </div>

  <script>
  function pct(v, d=1) { return (v*100).toFixed(d)+'%'; }
  function sign(v, d=2) { return (v>=0?'+':'')+(v*100).toFixed(d)+'%'; }
  function num(v, d=3) { return v.toFixed(d); }

  function drawLineChart(canvasId, series, colors, labels, yFormat) {
    const canvas = document.getElementById(canvasId);
    const dpr = window.devicePixelRatio || 1;
    const W = canvas.parentElement.clientWidth - 32;
    const H = 320;
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const PAD = { top: 20, right: 20, bottom: 30, left: 56 };
    const cw = W - PAD.left - PAD.right;
    const ch = H - PAD.top - PAD.bottom;

    const allVals = series.flat();
    let yMin = Math.min(...allVals);
    let yMax = Math.max(...allVals);
    const yRange = yMax - yMin || 1;
    yMin -= yRange * 0.04;
    yMax += yRange * 0.04;

    const n = series[0].length;

    // grid
    ctx.strokeStyle = '#1e2e48';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
      const y = PAD.top + (ch * i / 5);
      ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(PAD.left + cw, y); ctx.stroke();
      const val = yMax - (yMax - yMin) * i / 5;
      ctx.fillStyle = '#8d9bb5'; ctx.font = '11px Arial'; ctx.textAlign = 'right';
      ctx.fillText(yFormat(val), PAD.left - 6, y + 4);
    }

    // x-axis labels (every ~60 points)
    const xStep = Math.max(1, Math.floor(n / 8));
    for (let i = 0; i < n; i += xStep) {
      const x = PAD.left + (cw * i / (n - 1));
      const lbl = labels[i] ? labels[i].slice(0, 7) : '';
      ctx.fillStyle = '#8d9bb5'; ctx.textAlign = 'center';
      ctx.fillText(lbl, x, H - PAD.bottom + 16);
    }

    // series lines
    series.forEach((data, si) => {
      ctx.beginPath();
      ctx.strokeStyle = colors[si];
      ctx.lineWidth = si === 0 ? 2 : 1.5;
      data.forEach((v, i) => {
        const x = PAD.left + (cw * i / (n - 1));
        const y = PAD.top + ch * (1 - (v - yMin) / (yMax - yMin));
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.stroke();
    });
  }

  async function loadData() {
    const [latest, backtest, curve, tilts] = await Promise.all([
      fetch('/api/latest').then(r => r.json()),
      fetch('/api/backtest').then(r => r.json()),
      fetch('/api/equity-curve').then(r => r.json()),
      fetch('/api/tilts?limit=15').then(r => r.json()),
    ]);

    const reg = latest.regime.regime;
    const regEl = document.getElementById('regime');
    regEl.textContent = reg;
    regEl.className = 'val ' + reg;
    document.getElementById('confidence').textContent = pct(latest.regime.confidence);
    document.getElementById('tilt-eq').textContent = 'Equity ' + pct(latest.tilt.equity);
    document.getElementById('tilt-rest').textContent =
      'Bonds ' + pct(latest.tilt.bonds) + '  Cash ' + pct(latest.tilt.cash);

    document.getElementById('s-cagr').textContent = sign(backtest.cagr);
    document.getElementById('bm-cagr').textContent = sign(backtest.benchmark_cagr);
    document.getElementById('sharpe').textContent = num(backtest.sharpe);
    document.getElementById('alpha').textContent = num(backtest.alpha);
    document.getElementById('beta').textContent = num(backtest.beta);
    document.getElementById('mdd').textContent = sign(backtest.max_drawdown);
    document.getElementById('bm-mdd').textContent = sign(backtest.benchmark_max_drawdown);
    document.getElementById('ir').textContent = num(backtest.information_ratio);
    document.getElementById('excess').textContent = sign(backtest.excess_return);

    // charts
    const days = curve.map(p => p.day);
    drawLineChart('chart',
      [curve.map(p => p.strategy_equity), curve.map(p => p.benchmark_equity)],
      ['#4edc8a', '#8ec5ff'], days, v => v.toFixed(2));
    drawLineChart('ddchart',
      [curve.map(p => p.strategy_drawdown), curve.map(p => p.benchmark_drawdown)],
      ['#4edc8a', '#8ec5ff'], days, v => pct(v));

    // table
    const tbody = document.getElementById('regime-table');
    tbody.innerHTML = '';
    tilts.items.slice().reverse().forEach(t => {
      const cls = t.regime;
      tbody.innerHTML += '<tr>' +
        '<td>' + t.day + '</td>' +
        '<td class="' + cls + '">' + t.regime + '</td>' +
        '<td>' + pct(t.confidence) + '</td>' +
        '<td>' + pct(t.equity) + '</td>' +
        '<td>' + pct(t.bonds) + '</td>' +
        '<td>' + pct(t.cash) + '</td></tr>';
    });
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

            if parsed.path == "/api/equity-curve":
                qs = parse_qs(parsed.query)
                limit = int(qs.get("limit", [len(snapshot["equity_curve"])])[0])
                items = snapshot["equity_curve"][-max(1, limit):]
                self._json(items)
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
    print("API endpoints: /api/health, /api/latest, /api/backtest, /api/equity-curve, /api/regimes, /api/tilts, /api/meta")
    server.serve_forever()

