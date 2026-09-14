"""Gas-dashboard read use cases over validated derived data."""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ..errors import DataFormatError, DataUnavailableError


DEFAULT_GAS_DATA = Path(__file__).resolve().parents[3] / "gas" / "data" / "processed_data.csv"
REQUIRED_FIELDS = ("Timestamp", "Odometer", "Gallons", "Total Cost", "MilesPerTank", "TripMPG", "CostPerMile")


def get_gas_dashboard(data_path: Path = DEFAULT_GAS_DATA) -> dict[str, Any]:
    """Return traceable processed observations and deterministic summary values."""

    if not data_path.exists():
        raise DataUnavailableError("Gas data has not been processed yet. Run './run gas'.")
    with data_path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        missing = [field for field in REQUIRED_FIELDS if field not in (reader.fieldnames or ())]
        if missing:
            raise DataFormatError(f"Processed gas data is missing fields: {', '.join(missing)}")
        rows = list(reader)

    try:
        total_cost = sum((_decimal(row["Total Cost"]) for row in rows), Decimal("0"))
        total_gallons = sum((_decimal(row["Gallons"]) for row in rows), Decimal("0"))
        total_miles = sum((_decimal(row["MilesPerTank"]) for row in rows), Decimal("0"))
        average_mpg = (
            sum((_decimal(row["TripMPG"]) for row in rows), Decimal("0")) / Decimal(len(rows))
            if rows else None
        )
    except (InvalidOperation, KeyError) as error:
        raise DataFormatError("Processed gas data contains malformed numeric values.") from error

    return {
        "summary": {
            "record_count": len(rows),
            "total_cost": _json_decimal(total_cost),
            "total_gallons": _json_decimal(total_gallons),
            "total_miles": _json_decimal(total_miles),
            "average_trip_mpg": None if average_mpg is None else _json_decimal(average_mpg),
        },
        "records": rows,
    }


def _decimal(value: str) -> Decimal:
    decimal = Decimal(value)
    if not decimal.is_finite():
        raise InvalidOperation
    return decimal


def _json_decimal(value: Decimal) -> str:
    return format(value, "f")
