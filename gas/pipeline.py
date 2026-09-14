"""File-based gas ingestion pipeline for the current Google Sheet export.

The Google Sheet downloader writes ``live_data.csv``. This module validates it,
records rejected source rows separately, and produces the analytics CSV used by
the existing Shiny dashboard. It does not connect to PostgreSQL or alter source
records.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Mapping

from .normalization import GasEntry, RejectedGasRow, normalize_gas_rows


ANALYTICS_FIELDS = (
    "Timestamp", "Odometer", "Gallons", "Total Cost", "Vehicle", "Station", "Notes",
    "Source Name", "Source Row", "Source Fingerprint", "MilesPerTank", "TripMPG",
    "TripMPG_clean", "RollingMPG_mean", "Month", "Year", "PricePerGallon",
    "CostPerMile", "CostPerMile_MA10",
)


@dataclass(frozen=True)
class GasPipelineResult:
    analytics_rows: tuple[dict[str, str], ...]
    rejected_rows: tuple[RejectedGasRow, ...]


def build_gas_analytics(
    rows: Iterable[Mapping[str, object]], *, source_name: str
) -> GasPipelineResult:
    """Validate observed purchases and calculate the existing dashboard metrics.

    The calculation remains deterministic and only emits records with a valid
    prior odometer reading, as the former processor did.
    """

    normalized = normalize_gas_rows(rows, source_name=source_name)
    entries = sorted(normalized.entries, key=lambda entry: (entry.odometer, entry.occurred_at))
    analytics: list[dict[str, str]] = []
    rejected = list(normalized.rejected_rows)
    clean_mpg: list[Decimal] = []
    cost_per_mile: list[Decimal] = []
    previous: GasEntry | None = None

    for entry in entries:
        if previous is None:
            previous = entry
            continue
        miles = entry.odometer - previous.odometer
        previous = entry
        if miles <= 0:
            rejected.append(RejectedGasRow(entry.source_row, "odometer must increase between purchases", entry.raw_source))
            continue
        trip_mpg = miles / entry.gallons
        clipped_mpg = min(max(trip_mpg, Decimal("15")), Decimal("40"))
        clean_mpg.append(clipped_mpg)
        price_per_gallon = entry.total_cost / entry.gallons
        per_mile = entry.total_cost / miles
        cost_per_mile.append(per_mile)
        analytics.append(_analytics_row(entry, miles, trip_mpg, clipped_mpg, clean_mpg, price_per_gallon, per_mile, cost_per_mile))

    return GasPipelineResult(tuple(analytics), tuple(rejected))


def run_pipeline(input_path: Path, output_path: Path, rejected_path: Path, *, source_name: str) -> GasPipelineResult:
    """Run the CSV ingestion path with atomic derived-data writes."""

    with input_path.open(newline="", encoding="utf-8-sig") as source:
        result = build_gas_analytics(csv.DictReader(source), source_name=source_name)
    _atomic_write_csv(output_path, ANALYTICS_FIELDS, result.analytics_rows)
    _atomic_write_csv(
        rejected_path,
        ("Source Row", "Reason", "Raw Source"),
        ({"Source Row": row.source_row, "Reason": row.reason, "Raw Source": repr(row.raw_source)} for row in result.rejected_rows),
    )
    return result


def _analytics_row(entry: GasEntry, miles: Decimal, trip_mpg: Decimal, clipped_mpg: Decimal, clean_mpg: list[Decimal], price_per_gallon: Decimal, per_mile: Decimal, cost_per_mile: list[Decimal]) -> dict[str, str]:
    rolling_mpg = sum(clean_mpg[-5:]) / Decimal(len(clean_mpg[-5:]))
    ma10 = "" if len(cost_per_mile) < 2 else _number(sum(cost_per_mile[-10:]) / Decimal(len(cost_per_mile[-10:])))
    return {
        "Timestamp": entry.occurred_at.isoformat(), "Odometer": _number(entry.odometer),
        "Gallons": _number(entry.gallons), "Total Cost": _number(entry.total_cost),
        "Vehicle": entry.vehicle or "", "Station": entry.station or "", "Notes": entry.notes or "",
        "Source Name": entry.source_name, "Source Row": str(entry.source_row),
        "Source Fingerprint": entry.source_fingerprint, "MilesPerTank": _number(miles),
        "TripMPG": _number(trip_mpg), "TripMPG_clean": _number(clipped_mpg),
        "RollingMPG_mean": _number(rolling_mpg), "Month": entry.occurred_at.strftime("%Y-%m"),
        "Year": str(entry.occurred_at.year), "PricePerGallon": _number(price_per_gallon),
        "CostPerMile": _number(per_mile), "CostPerMile_MA10": ma10,
    }


def _atomic_write_csv(path: Path, fieldnames: tuple[str, ...], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def _number(value: Decimal) -> str:
    return format(value, "f")
