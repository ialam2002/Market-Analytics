from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimePoint:
    day: str
    regime: str
    confidence: float


def _safe(value: float | None, fallback: float = 0.0) -> float:
    return fallback if value is None else value


def classify_regimes(feature_frame: list[dict[str, float | str | None]]) -> list[RegimePoint]:
    """Simple interpretable classifier for market risk regime detection."""
    output: list[RegimePoint] = []

    for row in feature_frame:
        m20 = _safe(row["momentum_20"] if isinstance(row["momentum_20"], float) else None)
        v20 = _safe(row["volatility_20"] if isinstance(row["volatility_20"], float) else None)
        d60 = _safe(row["drawdown_60"] if isinstance(row["drawdown_60"], float) else None)
        vix = _safe(row["vix"] if isinstance(row["vix"], float) else None, fallback=20.0)

        if (m20 > 0.015 and v20 < 0.014 and d60 > -0.09 and vix < 24.0):
            regime = "RISK_ON"
            confidence = min(1.0, 0.55 + m20 * 8.0)
        elif (m20 < -0.01 or v20 > 0.022 or d60 < -0.13 or vix > 30.0):
            regime = "RISK_OFF"
            confidence = min(1.0, 0.6 + abs(m20) * 6.0 + max(0.0, v20 - 0.02) * 8.0)
        else:
            regime = "TRANSITION"
            confidence = 0.55

        output.append(RegimePoint(day=str(row["day"]), regime=regime, confidence=round(confidence, 4)))

    return output


def build_portfolio_tilts(regimes: list[RegimePoint]) -> list[dict[str, float | str]]:
    """Map regimes to tactical allocations to show business use-case value."""
    tilts: list[dict[str, float | str]] = []

    for point in regimes:
        if point.regime == "RISK_ON":
            allocation = {"equity": 0.72, "bonds": 0.22, "cash": 0.06}
        elif point.regime == "RISK_OFF":
            allocation = {"equity": 0.28, "bonds": 0.52, "cash": 0.20}
        else:
            allocation = {"equity": 0.50, "bonds": 0.38, "cash": 0.12}

        tilts.append(
            {
                "day": point.day,
                "regime": point.regime,
                "confidence": point.confidence,
                "equity": allocation["equity"],
                "bonds": allocation["bonds"],
                "cash": allocation["cash"],
            }
        )

    return tilts

