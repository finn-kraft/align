"""File-based gas ingestion pipeline for the current Google Sheet export.

The Google Sheet downloader writes ``live_data.csv``. This module validates it,
records rejected source rows separately, and produces the analytics CSV used by
the existing Shiny dashboard. It does not connect to PostgreSQL or alter source
records.
"""

from __future__ import annotations

import csv
import argparse
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Mapping

from .normalization import GasEntry, RejectedGasRow, normalize_gas_rows
from .source_csv import read_gas_source_csv


ANALYTICS_FIELDS = (
    "Timestamp", "Odometer", "Gallons", "Total Cost", "Vehicle", "Station", "Notes",
    "Source Name", "Source Row", "Source Fingerprint", "MilesPerTank", "TripMPG",
    "TripMPG_clean", "RollingMPG_mean", "Month", "Year", "PricePerGallon",
    "CostPerMile", "CostPerMile_MA10", "Data Quality", "Quality Flags",
)


@dataclass(frozen=True)
class GasQualityIssue:
    source_row: int
    code: str
    message: str
    excludes_efficiency: bool = False
    excludes_cost_per_mile: bool = False


@dataclass(frozen=True)
class GasPipelineResult:
    analytics_rows: tuple[dict[str, str], ...]
    rejected_rows: tuple[RejectedGasRow, ...]
    quality_issues: tuple[GasQualityIssue, ...] = ()


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
    quality_issues: list[GasQualityIssue] = []
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
        price_per_gallon = entry.total_cost / entry.gallons
        per_mile = entry.total_cost / miles
        issues = _quality_issues(entry, miles, trip_mpg, price_per_gallon)
        quality_issues.extend(issues)
        reliable_efficiency = not any(issue.excludes_efficiency for issue in issues)
        reliable_cost = not any(issue.excludes_cost_per_mile for issue in issues)
        cleaned_mpg = trip_mpg if reliable_efficiency else None
        if cleaned_mpg is not None:
            clean_mpg.append(cleaned_mpg)
        if reliable_cost:
            cost_per_mile.append(per_mile)
        analytics.append(
            _analytics_row(
                entry, miles, trip_mpg, cleaned_mpg, clean_mpg,
                price_per_gallon, per_mile if reliable_cost else None,
                cost_per_mile, issues,
            )
        )

    return GasPipelineResult(tuple(analytics), tuple(rejected), tuple(quality_issues))


def run_pipeline(input_path: Path, output_path: Path, rejected_path: Path, *, source_name: str, default_vehicle: str | None = None) -> GasPipelineResult:
    """Run the CSV ingestion path with atomic derived-data writes."""

    source = read_gas_source_csv(input_path, default_vehicle=default_vehicle)
    result = build_gas_analytics(source.rows, source_name=source_name)
    _atomic_write_csv(output_path, ANALYTICS_FIELDS, result.analytics_rows)
    _atomic_write_csv(
        rejected_path,
        ("Source Row", "Reason", "Raw Source"),
        ({"Source Row": row.source_row, "Reason": row.reason, "Raw Source": repr(row.raw_source)} for row in result.rejected_rows),
    )
    return result


def _analytics_row(entry: GasEntry, miles: Decimal, trip_mpg: Decimal, cleaned_mpg: Decimal | None, clean_mpg: list[Decimal], price_per_gallon: Decimal, per_mile: Decimal | None, cost_per_mile: list[Decimal], issues: list[GasQualityIssue]) -> dict[str, str]:
    rolling_mpg = "" if not clean_mpg else _number(sum(clean_mpg[-5:]) / Decimal(len(clean_mpg[-5:])))
    ma10 = "" if len(cost_per_mile) < 2 else _number(sum(cost_per_mile[-10:]) / Decimal(len(cost_per_mile[-10:])))
    return {
        "Timestamp": entry.occurred_at.isoformat(), "Odometer": _number(entry.odometer),
        "Gallons": _number(entry.gallons), "Total Cost": _number(entry.total_cost),
        "Vehicle": entry.vehicle or "", "Station": entry.station or "", "Notes": entry.notes or "",
        "Source Name": entry.source_name, "Source Row": str(entry.source_row),
        "Source Fingerprint": entry.source_fingerprint, "MilesPerTank": _number(miles),
        "TripMPG": _number(trip_mpg), "TripMPG_clean": "" if cleaned_mpg is None else _number(cleaned_mpg),
        "RollingMPG_mean": rolling_mpg, "Month": entry.occurred_at.strftime("%Y-%m"),
        "Year": str(entry.occurred_at.year), "PricePerGallon": _number(price_per_gallon),
        "CostPerMile": "" if per_mile is None else _number(per_mile), "CostPerMile_MA10": ma10,
        "Data Quality": "ok" if not issues else "excluded" if any(issue.excludes_efficiency or issue.excludes_cost_per_mile for issue in issues) else "warning",
        "Quality Flags": ";".join(issue.code for issue in issues),
    }


def _quality_issues(entry: GasEntry, miles: Decimal, trip_mpg: Decimal, price_per_gallon: Decimal) -> list[GasQualityIssue]:
    issues: list[GasQualityIssue] = []
    notes = (entry.notes or "").casefold()
    if "missing data" in notes or "missing fill" in notes:
        issues.append(GasQualityIssue(entry.source_row, "missing_fills", "Source notes report missing fill records.", True, True))
    if miles > Decimal("800") and entry.gallons > Decimal("20") and Decimal("15") <= trip_mpg <= Decimal("50"):
        issues.append(GasQualityIssue(entry.source_row, "aggregated_fills", "Distance and fuel quantity suggest multiple fills were combined."))
    elif miles > Decimal("800"):
        issues.append(GasQualityIssue(entry.source_row, "large_distance_gap", "Distance since the prior record exceeds 800 miles.", True, True))
    if entry.gallons < Decimal("3"):
        issues.append(GasQualityIssue(entry.source_row, "possible_partial_fill", "Fuel quantity is below 3 gallons.", True, False))
    if entry.gallons > Decimal("20") and not any(issue.code == "aggregated_fills" for issue in issues):
        issues.append(GasQualityIssue(entry.source_row, "large_fuel_quantity", "Fuel quantity exceeds 20 gallons and may aggregate fills."))
    if trip_mpg < Decimal("15") or trip_mpg > Decimal("50"):
        issues.append(GasQualityIssue(entry.source_row, "implausible_mpg", "Calculated MPG is outside the 15-50 review range.", True, True))
    if price_per_gallon < Decimal("1.5") or price_per_gallon > Decimal("8"):
        issues.append(GasQualityIssue(entry.source_row, "implausible_price", "Calculated fuel price is outside the $1.50-$8.00 review range.", False, True))
    return issues


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and process Align gas source data.")
    parser.add_argument("--input", type=Path, default=Path(__file__).parent / "data" / "live_data.csv")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "data" / "processed_data.csv")
    parser.add_argument("--rejected", type=Path, default=Path(__file__).parent / "data" / "rejected_rows.csv")
    parser.add_argument("--source-name", default="google-sheet:jetta")
    parser.add_argument("--vehicle", default="Jetta")
    arguments = parser.parse_args()
    if not arguments.input.exists():
        raise SystemExit(f"No gas source file found: {arguments.input}")
    result = run_pipeline(arguments.input, arguments.output, arguments.rejected, source_name=arguments.source_name, default_vehicle=arguments.vehicle)
    print(f"Processed {len(result.analytics_rows)} dashboard rows; rejected {len(result.rejected_rows)} source rows; flagged {len(result.quality_issues)} quality issues.")


if __name__ == "__main__":
    main()
