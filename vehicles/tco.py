"""Deterministic vehicle total-cost-of-ownership calculations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


CostBasis = Literal["observed", "assumption"]


@dataclass(frozen=True)
class OwnershipCost:
    """One named ownership cost with an explicit evidentiary basis."""

    name: str
    amount: Decimal
    basis: CostBasis

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("cost name is required")
        if self.amount < 0:
            raise ValueError("cost amount must not be negative")
        if self.basis not in ("observed", "assumption"):
            raise ValueError("cost basis must be observed or assumption")


@dataclass(frozen=True)
class VehicleTcoScenario:
    """A reproducible ownership scenario; it does not infer missing costs."""

    vehicle_name: str
    duration_months: int
    costs: tuple[OwnershipCost, ...]
    expected_resale_value: Decimal = Decimal("0")
    starting_odometer: Decimal | None = None
    ending_odometer: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.vehicle_name.strip():
            raise ValueError("vehicle name is required")
        if self.duration_months <= 0:
            raise ValueError("duration_months must be greater than zero")
        if self.expected_resale_value < 0:
            raise ValueError("expected resale value must not be negative")
        if (self.starting_odometer is None) != (self.ending_odometer is None):
            raise ValueError("both odometer readings are required to calculate miles")
        if self.starting_odometer is not None and self.ending_odometer is not None:
            if self.ending_odometer < self.starting_odometer:
                raise ValueError("ending odometer must not be less than starting odometer")


@dataclass(frozen=True)
class VehicleTcoResult:
    gross_cost: Decimal
    observed_cost: Decimal
    assumed_cost: Decimal
    expected_resale_value: Decimal
    net_cost: Decimal
    months: int
    miles: Decimal | None
    net_cost_per_month: Decimal
    net_cost_per_mile: Decimal | None


def calculate_tco(scenario: VehicleTcoScenario) -> VehicleTcoResult:
    """Calculate TCO from declared values only; no LLM or hidden estimates."""

    observed = sum((cost.amount for cost in scenario.costs if cost.basis == "observed"), Decimal("0"))
    assumed = sum((cost.amount for cost in scenario.costs if cost.basis == "assumption"), Decimal("0"))
    gross = observed + assumed
    net = gross - scenario.expected_resale_value
    miles = None
    per_mile = None
    if scenario.starting_odometer is not None and scenario.ending_odometer is not None:
        miles = scenario.ending_odometer - scenario.starting_odometer
        if miles > 0:
            per_mile = net / miles
    return VehicleTcoResult(
        gross_cost=gross,
        observed_cost=observed,
        assumed_cost=assumed,
        expected_resale_value=scenario.expected_resale_value,
        net_cost=net,
        months=scenario.duration_months,
        miles=miles,
        net_cost_per_month=net / Decimal(scenario.duration_months),
        net_cost_per_mile=per_mile,
    )
