from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import csv
import io
from pathlib import Path
from typing import Callable
from urllib.error import URLError
from urllib.request import urlopen

from .synthetic_data import MarketRow, generate_market_data


@dataclass(frozen=True)
class LoadResult:
    rows: list[MarketRow]
    source_used: str
    note: str


def _parse_iso_day(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_stooq_series(csv_text: str) -> dict[date, float]:
    reader = csv.DictReader(io.StringIO(csv_text))
    out: dict[date, float] = {}

    for row in reader:
        day_raw = row.get("Date")
        close_raw = row.get("Close")
        if not day_raw or not close_raw:
            continue
        if close_raw.upper() == "N/A":
            continue
        out[_parse_iso_day(day_raw)] = float(close_raw)

    return out


def _parse_fred_series(csv_text: str, key: str) -> dict[date, float]:
    reader = csv.DictReader(io.StringIO(csv_text))
    out: dict[date, float] = {}

    for row in reader:
        day_raw = row.get("DATE")
        val_raw = row.get(key)
        if not day_raw or not val_raw or val_raw == ".":
            continue
        out[_parse_iso_day(day_raw)] = float(val_raw)

    return out


def _download_text(url: str, timeout: int = 12) -> str:
    with urlopen(url, timeout=timeout) as response:  # nosec B310 - public data feed URL
        return response.read().decode("utf-8")


def _rows_from_series(
    price: dict[date, float],
    benchmark: dict[date, float],
    vix: dict[date, float],
    rate_10y: dict[date, float],
    days: int,
) -> list[MarketRow]:
    common_days = sorted(set(price) & set(benchmark) & set(vix) & set(rate_10y))
    if not common_days:
        return []

    selected = common_days[-days:]
    return [
        MarketRow(
            day=day,
            price=round(price[day], 4),
            benchmark=round(benchmark[day], 4),
            vix=round(vix[day], 4),
            rate_10y=round(rate_10y[day], 4),
        )
        for day in selected
    ]


def _load_live_public(days: int) -> list[MarketRow]:
    spy = _parse_stooq_series(_download_text("https://stooq.com/q/d/l/?s=spy.us&i=d"))
    spx = _parse_stooq_series(_download_text("https://stooq.com/q/d/l/?s=%5Espx&i=d"))
    vix = _parse_fred_series(
        _download_text("https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS"),
        "VIXCLS",
    )
    dgs10 = _parse_fred_series(
        _download_text("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"),
        "DGS10",
    )
    return _rows_from_series(spy, spx, vix, dgs10, days=days)


def _load_csv_file(csv_file: Path, days: int) -> list[MarketRow]:
    with csv_file.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[MarketRow] = []

        for row in reader:
            rows.append(
                MarketRow(
                    day=_parse_iso_day(row["day"]),
                    price=float(row["price"]),
                    benchmark=float(row["benchmark"]),
                    vix=float(row["vix"]),
                    rate_10y=float(row["rate_10y"]),
                )
            )

    rows.sort(key=lambda item: item.day)
    return rows[-days:]


def load_market_data(
    source: str,
    days: int,
    seed: int,
    csv_file: Path | None = None,
    live_loader: Callable[[int], list[MarketRow]] | None = None,
) -> LoadResult:
    """Load market rows from synthetic, CSV, or public live feeds with fallback."""
    normalized = source.strip().lower()

    if normalized == "synthetic":
        return LoadResult(
            rows=generate_market_data(days=days, seed=seed),
            source_used="synthetic",
            note="generated synthetic data",
        )

    if normalized == "csv":
        if csv_file is None:
            raise ValueError("csv_file must be provided when source='csv'")
        rows = _load_csv_file(csv_file=csv_file, days=days)
        return LoadResult(rows=rows, source_used="csv", note=f"loaded {len(rows)} rows from CSV")

    if normalized != "live":
        raise ValueError("source must be one of: synthetic, csv, live")

    loader = _load_live_public if live_loader is None else live_loader
    try:
        rows = loader(days)
        if len(rows) < 60:
            raise ValueError("insufficient live rows")
        return LoadResult(rows=rows, source_used="live", note=f"loaded {len(rows)} rows from public feeds")
    except (URLError, TimeoutError, ValueError):
        fallback = generate_market_data(days=days, seed=seed)
        return LoadResult(
            rows=fallback,
            source_used="synthetic-fallback",
            note="live data unavailable, used synthetic fallback",
        )

