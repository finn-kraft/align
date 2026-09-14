"""Deterministic data contracts for tracking vehicle total cost of ownership."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal
from uuid import UUID


CostCategory = Literal["purchase", "maintenance", "repair", "administrative", "fuel", "other"]
VALID_COST_CATEGORIES = frozenset({"purchase", "maintenance", "repair", "administrative", "fuel", "other"})
CENT = Decimal("0.01")


def as_money(value: Decimal | int | float | str) -> Decimal:
    """Return a non-negative, cent-precise monetary value."""
    amount = Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    if amount < 0:
        raise ValueError("Ownership costs must be zero or greater.")
    return amount


@dataclass(frozen=True)
class Vehicle:
    """One owned vehicle, separate from its cost-event history."""

    id: UUID
    name: str
    make: str | None
    model: str | None
    year: int | None
    acquired_on: date
    starting_odometer: Decimal | None
    created_at: datetime | None = None


@dataclass(frozen=True)
class VehicleCostEvent:
    """An immutable observed ownership cost such as an oil change or repair."""

    vehicle_id: UUID
    occurred_on: date
    category: CostCategory
    service_type: str
    amount: Decimal
    description: str | None = None
    odometer: Decimal | None = None
    notes: str | None = None
    id: UUID | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Reject invalid categories and blank service labels before persistence."""
        if self.category not in VALID_COST_CATEGORIES:
            raise ValueError("Unsupported ownership cost category.")
        if not self.service_type.strip():
            raise ValueError("A service type is required (for example, Oil change).")
        object.__setattr__(self, "amount", as_money(self.amount))
        if self.odometer is not None and Decimal(str(self.odometer)) < 0:
            raise ValueError("Odometer cannot be negative.")


@dataclass(frozen=True)
class VehicleOwnershipSummary:
    """A stored-cost summary; it never estimates or recalculates source events."""

    vehicle_id: UUID
    vehicle_name: str
    total_cost: Decimal
    purchase_cost: Decimal
    maintenance_cost: Decimal
    repair_cost: Decimal
    administrative_cost: Decimal
    fuel_cost: Decimal
    other_cost: Decimal
    event_count: int
