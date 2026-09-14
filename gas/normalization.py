"""Validation and normalization for observed fuel-purchase source rows.

This module deliberately has no Google Sheets, pandas, database, or UI
dependency.  It turns source rows into typed observations while retaining the
source row and a stable fingerprint for audit and deduplication.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class GasEntry:
    """One validated, observed fuel purchase (not a forecast or assumption)."""

    occurred_at: datetime
    odometer: Decimal
    gallons: Decimal
    total_cost: Decimal
    vehicle: str | None
    station: str | None
    notes: str | None
    source_name: str
    source_row: int
    source_fingerprint: str
    raw_source: dict[str, Any]


@dataclass(frozen=True)
class RejectedGasRow:
    source_row: int
    reason: str
    raw_source: dict[str, Any]


@dataclass(frozen=True)
class GasNormalizationResult:
    entries: tuple[GasEntry, ...]
    rejected_rows: tuple[RejectedGasRow, ...]


_ALIASES = {
    "timestamp": ("Timestamp", "Date", "date", "timestamp"),
    "odometer": ("Odometer", "odometer", "Mileage", "mileage"),
    "gallons": ("Gallons", "gallons", "Gallons Purchased", "gallons_purchased"),
    "total_cost": ("Total Cost", "total_cost", "Cost", "cost", "Amount", "amount"),
    "vehicle": ("Vehicle", "vehicle"),
    "station": ("Station", "station"),
    "notes": ("Notes", "notes", "Description", "description"),
}


def normalize_gas_rows(
    rows: Iterable[Mapping[str, Any]], *, source_name: str
) -> GasNormalizationResult:
    """Normalize rows from an external gas source without silently discarding errors.

    Duplicate observations are rejected rather than merged so an ingestion
    caller can surface and audit them before persistence.  ``source_row`` is
    one-based and excludes the source header row.
    """

    source_name = _required_text(source_name, "source_name")
    entries: list[GasEntry] = []
    rejected: list[RejectedGasRow] = []
    fingerprints: set[str] = set()

    for sequence, row in enumerate(rows, start=1):
        raw = dict(row)
        raw_source_row = raw.pop("__source_row__", sequence)
        try:
            source_row = int(raw_source_row)
        except (TypeError, ValueError) as error:
            raise ValueError("source row marker must be an integer") from error
        try:
            occurred_at = _parse_datetime(_value(raw, "timestamp"))
            odometer = _positive_decimal(_value(raw, "odometer"), "odometer")
            gallons = _positive_decimal(_value(raw, "gallons"), "gallons")
            total_cost = _nonnegative_decimal(_value(raw, "total_cost"), "total_cost")
            vehicle = _optional_text(_value(raw, "vehicle"))
            station = _optional_text(_value(raw, "station"))
            notes = _optional_text(_value(raw, "notes"))
            fingerprint = _fingerprint(
                occurred_at, odometer, gallons, total_cost, vehicle, station
            )
        except ValueError as error:
            rejected.append(RejectedGasRow(source_row, str(error), raw))
            continue

        if fingerprint in fingerprints:
            rejected.append(RejectedGasRow(source_row, "duplicate observed fuel purchase", raw))
            continue
        fingerprints.add(fingerprint)
        entries.append(
            GasEntry(
                occurred_at=occurred_at,
                odometer=odometer,
                gallons=gallons,
                total_cost=total_cost,
                vehicle=vehicle,
                station=station,
                notes=notes,
                source_name=source_name,
                source_row=source_row,
                source_fingerprint=fingerprint,
                raw_source=raw,
            )
        )

    return GasNormalizationResult(tuple(entries), tuple(rejected))


def _value(row: Mapping[str, Any], field: str) -> Any:
    for alias in _ALIASES[field]:
        if alias in row:
            return row[alias]
    return None


def _parse_datetime(value: Any) -> datetime:
    text = _required_text(value, "timestamp")
    candidates = (text, text.replace("Z", "+00:00"))
    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass
    for format_string in ("%m/%d/%Y", "%m/%d/%Y %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, format_string)
        except ValueError:
            pass
    raise ValueError("timestamp is malformed")


def _positive_decimal(value: Any, field: str) -> Decimal:
    decimal = _decimal(value, field)
    if decimal <= 0:
        raise ValueError(f"{field} must be greater than zero")
    return decimal


def _nonnegative_decimal(value: Any, field: str) -> Decimal:
    decimal = _decimal(value, field)
    if decimal < 0:
        raise ValueError(f"{field} must not be negative")
    return decimal


def _decimal(value: Any, field: str) -> Decimal:
    text = _required_text(value, field).replace(",", "").replace("$", "")
    try:
        decimal = Decimal(text)
    except InvalidOperation as error:
        raise ValueError(f"{field} is malformed") from error
    if not decimal.is_finite():
        raise ValueError(f"{field} is malformed")
    return decimal


def _required_text(value: Any, field: str) -> str:
    text = _optional_text(value)
    if text is None:
        raise ValueError(f"{field} is required")
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _fingerprint(
    occurred_at: datetime,
    odometer: Decimal,
    gallons: Decimal,
    total_cost: Decimal,
    vehicle: str | None,
    station: str | None,
) -> str:
    canonical = "|".join(
        (
            occurred_at.isoformat(),
            str(odometer.normalize()),
            str(gallons.normalize()),
            str(total_cost.normalize()),
            vehicle or "",
            station or "",
        )
    )
    return sha256(canonical.encode("utf-8")).hexdigest()
