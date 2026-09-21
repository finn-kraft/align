"""Cash-flow integration for the electricity forecasting engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

TMAX = "TMAX (Degrees Fahrenheit)"
TMIN = "TMIN (Degrees Fahrenheit)"
CLIMATOLOGY_FILE = Path(__file__).with_name("electricity_climatology.csv")


def forecast_to_cashflow_months(
    forecast_rows: Iterable[Mapping[str, Any]] | pd.DataFrame,
) -> dict[str, dict[str, float]]:
    """Map forecast billing rows into the cash-flow model's monthly inputs."""
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
        if "utilities" in values:
            merged.setdefault(key, {})["utilities"] = round(float(values["utilities"]), 2)
    return merged


def build_average_weather(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Build weather from the bundled calendar-day temperature climatology."""
    profile = pd.read_csv(CLIMATOLOGY_FILE).set_index("calendar_day")
    dates = pd.date_range(
        pd.Timestamp(start).normalize(),
        pd.Timestamp(end).normalize(),
        freq="D",
    )
    calendar_days = pd.Series(dates.strftime("%m-%d"), index=dates)
    weather = pd.DataFrame(
        {
            "Date": dates,
            TMAX: calendar_days.map(profile[TMAX]).to_numpy(),
            TMIN: calendar_days.map(profile[TMIN]).to_numpy(),
        }
    )
    if weather[[TMAX, TMIN]].isna().any().any():
        raise ValueError("The bundled electricity climatology is incomplete")
    return weather


def build_occupancy_schedule(
    start: pd.Timestamp,
    end: pd.Timestamp,
    occupied_from: pd.Timestamp,
    occupied_through: pd.Timestamp,
) -> pd.DataFrame:
    """Create daily occupancy values from the user's move-in date range."""
    dates = pd.date_range(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize(), freq="D")
    first = pd.Timestamp(occupied_from).normalize()
    last = pd.Timestamp(occupied_through).normalize()
    if last < first:
        raise ValueError("Occupancy end date must be on or after the start date")
    return pd.DataFrame({"Date": dates, "Occupied": dates.to_series().between(first, last).astype(int).to_numpy()})


def uploaded_file_path(upload_value: Any) -> Path:
    """Extract a path from Shiny's input_file result."""
    if not upload_value:
        raise ValueError("Upload usage.csv before forecasting")
    item = upload_value[0] if isinstance(upload_value, list) else upload_value
    path = item.get("datapath") if isinstance(item, dict) else getattr(item, "datapath", None)
    if not path:
        raise ValueError("The uploaded usage file could not be read")
    result = Path(path)
    if not result.is_file():
        raise ValueError("The uploaded usage file is no longer available")
    return result


def validate_occupancy_dates(
    occupied_from: Any,
    occupied_through: Any,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    try:
        first = pd.Timestamp(occupied_from)
        last = pd.Timestamp(occupied_through)
    except (TypeError, ValueError) as error:
        raise ValueError("Occupancy dates must be valid dates") from error
    if pd.isna(first) or pd.isna(last):
        raise ValueError("Occupancy start and end dates are required")
    if last < first:
        raise ValueError("Occupancy end date must be on or after the start date")
    return first, last
