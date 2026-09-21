"""Cash-flow integration for the electricity forecasting engine.

The forecaster returns billing-period rows with a Predicted Bill column.
This adapter converts those rows into the existing cash-flow contract:
monthly input dictionaries with a utilities value.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd


def forecast_to_cashflow_months(
    forecast_rows: Iterable[Mapping[str, Any]] | pd.DataFrame,
) -> dict[str, dict[str, float]]:
    """Map forecast billing rows into the cash-flow model's monthly inputs.

    Rows are grouped by calendar month. If more than one billing period
    overlaps a month, the predicted bills are summed.
    """
    frame = (
        forecast_rows.copy()
        if isinstance(forecast_rows, pd.DataFrame)
        else pd.DataFrame(list(forecast_rows))
    )
    required = {"Billing From", "Predicted Bill"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Electricity forecast is missing: {', '.join(sorted(missing))}")
    if frame.empty:
        return {}

    frame["Billing From"] = pd.to_datetime(frame["Billing From"], errors="raise")
    frame["Predicted Bill"] = pd.to_numeric(frame["Predicted Bill"], errors="raise")
    if frame["Predicted Bill"].isna().any() or (frame["Predicted Bill"] < 0).any():
        raise ValueError("Electricity forecast bills must be finite non-negative numbers")

    grouped = frame.groupby(frame["Billing From"].dt.to_period("M"))["Predicted Bill"].sum()
    return {
        f"{period.year}_{period.month:02d}": {"utilities": round(float(amount), 2)}
        for period, amount in grouped.items()
    }


def merge_electricity_into_month_inputs(
    monthly_inputs: Mapping[str, Mapping[str, Any]],
    electricity_months: Mapping[str, Mapping[str, float]],
) -> dict[str, dict[str, Any]]:
    """Return monthly inputs with forecast electricity replacing utilities."""
    merged = {key: dict(values) for key, values in monthly_inputs.items()}
    for key, values in electricity_months.items():
        if "utilities" not in values:
            continue
        merged.setdefault(key, {})["utilities"] = round(float(values["utilities"]), 2)
    return merged


def validate_electricity_inputs(
    weather_path: str,
    usage_path: str,
    occupancy_path: str,
    through: str,
) -> tuple[Path, Path, Path, pd.Timestamp]:
    """Validate dialog values before running the engine."""
    paths = tuple(Path(value.strip()).expanduser() for value in
                  (weather_path, usage_path, occupancy_path))
    if any(not value for value in paths):
        raise ValueError("Weather, usage, and occupancy files are required")
    missing = [str(value) for value in paths if not value.is_file()]
    if missing:
        raise ValueError("Electricity input file not found: " + ", ".join(missing))
    try:
        end = pd.Timestamp(through)
    except (TypeError, ValueError) as error:
        raise ValueError("Forecast through date must be a valid date") from error
    if pd.isna(end):
        raise ValueError("Forecast through date must be a valid date")
    if end.date() < date.today():
        raise ValueError("Forecast through date must be today or later")
    return (*paths, end)
