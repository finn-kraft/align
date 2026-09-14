"""Immutable cash-flow saved-run snapshots."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping
from uuid import UUID, uuid4


MODEL_VERSION = "cashflow-simulator/v1"


@dataclass(frozen=True)
class SavedRunMonth:
    month_index: int
    month_start: date
    income: Decimal
    interest_income: Decimal
    recurring_expense: Decimal
    variable_expense: Decimal
    net_change: Decimal
    ending_cash: Decimal
    expense_categories: dict[str, Any]


@dataclass(frozen=True)
class SavedRunSnapshot:
    id: UUID
    model_version: str
    name: str
    notes: str | None
    start_date: date
    month_count: int
    starting_cash: Decimal
    apy: Decimal
    assumptions: dict[str, Any]
    months: tuple[SavedRunMonth, ...]


@dataclass(frozen=True)
class SavedRunSummary:
    """Metadata for an immutable saved run, without its monthly rows."""

    id: UUID
    created_at: datetime
    model_version: str
    name: str
    notes: str | None
    start_date: date
    month_count: int
    starting_cash: Decimal
    apy: Decimal


@dataclass(frozen=True)
class PersistedSavedRun:
    """A saved run exactly as stored, never recalculated on read."""

    summary: SavedRunSummary
    assumptions: dict[str, Any]
    months: tuple[SavedRunMonth, ...]


def _money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _month_start(label: str) -> date:
    return datetime.strptime(label, "%b %Y").date().replace(day=1)


def _month_key(label: str) -> str:
    value = _month_start(label)
    return f"{value.year}_{value.month:02d}"


def _expense_categories(month_input: Mapping[str, Any]) -> dict[str, Any]:
    categories: dict[str, Any] = {}
    other_label = str(month_input.get("other_label", "")).strip()

    for category, amount in month_input.items():
        if category in {"income", "other_label", "other_amount"}:
            continue
        categories[category] = _money(amount)

    if "other_amount" in month_input:
        categories["other"] = {
            "label": other_label,
            "amount": _money(month_input["other_amount"]),
        }

    return categories


def build_saved_run_snapshot(
    *,
    name: str,
    notes: str | None,
    state: Mapping[str, Any],
    monthly_inputs: Mapping[str, Mapping[str, Any]],
    projection: list[Mapping[str, Any]],
    run_id: UUID | None = None,
) -> SavedRunSnapshot:
    """Create a complete, immutable persistence payload for one projection."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("A saved run needs a name.")
    if not projection:
        raise ValueError("Run the simulation before saving it.")
    if len(projection) != state["months"]:
        raise ValueError("Projection length does not match the selected month count.")

    month_keys = [_month_key(str(row["Month"])) for row in projection]
    if len(set(month_keys)) != len(month_keys):
        raise ValueError("Projection months must be unique.")
    if set(monthly_inputs) != set(month_keys):
        raise ValueError("Monthly inputs must exactly match the projected months.")

    assumptions = {
        "recurring": dict(state["recurring"]),
        "monthly_inputs": {key: dict(monthly_inputs[key]) for key in month_keys},
    }
    snapshot_months = []
    for index, row in enumerate(projection):
        input_data = monthly_inputs[month_keys[index]]
        snapshot_months.append(
            SavedRunMonth(
                month_index=index,
                month_start=_month_start(str(row["Month"])),
                income=_money(row["Income"]),
                interest_income=_money(row["Interest Earned"]),
                recurring_expense=_money(row["Recurring"]),
                variable_expense=_money(row["Variable"]),
                net_change=_money(row["Net Change"]),
                ending_cash=_money(row["Ending Balance"]),
                expense_categories=_expense_categories(input_data),
            )
        )

    return SavedRunSnapshot(
        id=run_id or uuid4(),
        model_version=MODEL_VERSION,
        name=normalized_name,
        notes=notes.strip() if notes and notes.strip() else None,
        start_date=snapshot_months[0].month_start,
        month_count=state["months"],
        starting_cash=_money(state["starting_cash"]),
        apy=Decimal(str(state["apy"])),
        assumptions=assumptions,
        months=tuple(snapshot_months),
    )
