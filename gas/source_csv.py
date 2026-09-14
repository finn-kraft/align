"""Read irregular Google Sheet CSV exports without losing source traceability."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GasSourceRows:
    rows: tuple[dict[str, str], ...]
    header_row: int
    preamble: tuple[tuple[str, ...], ...]


def read_gas_source_csv(path: Path, *, default_vehicle: str | None = None) -> GasSourceRows:
    """Locate the real header in a Sheet export and return line-numbered rows.

    Google Sheets may export report labels and formulas above the response
    table. The reader searches for the required observed-data columns instead
    of assuming the first physical row is the header.
    """

    with path.open(newline="", encoding="utf-8-sig") as source:
        physical_rows = list(csv.reader(source))
    header_index = _find_header(physical_rows)
    headers = [header.strip() for header in physical_rows[header_index]]
    rows: list[dict[str, str]] = []
    for line_index, values in enumerate(physical_rows[header_index + 1 :], start=header_index + 2):
        if not any(value.strip() for value in values):
            continue
        padded = values + [""] * max(0, len(headers) - len(values))
        row = {header: padded[index].strip() for index, header in enumerate(headers) if header}
        row["__source_row__"] = str(line_index)
        if default_vehicle and not row.get("Vehicle"):
            row["Vehicle"] = default_vehicle
        rows.append(row)
    return GasSourceRows(
        rows=tuple(rows),
        header_row=header_index + 1,
        preamble=tuple(tuple(value for value in row) for row in physical_rows[:header_index]),
    )


def _find_header(rows: list[list[str]]) -> int:
    for index, row in enumerate(rows[:20]):
        normalized = {value.strip().casefold() for value in row}
        if {"timestamp", "odometer", "gallons", "total cost"}.issubset(normalized):
            return index
    raise ValueError("Could not find Timestamp, Odometer, Gallons, and Total Cost headers.")
