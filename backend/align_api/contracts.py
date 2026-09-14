"""Validated, framework-independent contracts for Align's public API."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any, Mapping

from cashflow.projection import MONTHS

from .errors import RequestValidationError
from vehicles.tco import OwnershipCost, VehicleTcoScenario


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise RequestValidationError(f"{field} must be numeric.")
    try:
        converted = float(value)
    except (TypeError, ValueError) as error:
        raise RequestValidationError(f"{field} must be numeric.") from error
    if not isfinite(converted):
        raise RequestValidationError(f"{field} must be finite.")
    return converted


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RequestValidationError(f"{field} must be an object.")
    return value


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool):
        raise RequestValidationError(f"{field} must be numeric.")
    try:
        converted = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise RequestValidationError(f"{field} must be numeric.") from error
    if not converted.is_finite():
        raise RequestValidationError(f"{field} must be finite.")
    return converted


@dataclass(frozen=True)
class CashflowProjectionRequest:
    months: int
    start_month: str
    starting_cash: float
    apy: float
    recurring: dict[str, float]
    monthly_inputs: dict[str, dict[str, float]]
    start_year: int | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "CashflowProjectionRequest":
        data = _mapping(payload, "request")
        raw_months = data.get("months")
        if isinstance(raw_months, bool):
            raise RequestValidationError("months must be a positive integer.")
        try:
            months = int(raw_months)
        except (TypeError, ValueError) as error:
            raise RequestValidationError("months must be a positive integer.") from error
        if months <= 0 or months > 120 or str(raw_months) not in {str(months), f"{months}.0"}:
            raise RequestValidationError("months must be a whole number from 1 through 120.")

        start_month = data.get("start_month")
        if start_month not in MONTHS:
            raise RequestValidationError("start_month must be a three-letter month abbreviation.")

        start_year = data.get("start_year")
        if start_year is not None:
            if isinstance(start_year, bool):
                raise RequestValidationError("start_year must be an integer.")
            try:
                start_year = int(start_year)
            except (TypeError, ValueError) as error:
                raise RequestValidationError("start_year must be an integer.") from error

        recurring_data = _mapping(data.get("recurring", {}), "recurring")
        monthly_data = _mapping(data.get("monthly_inputs", {}), "monthly_inputs")
        recurring = {
            str(category): _number(amount, f"recurring.{category}")
            for category, amount in recurring_data.items()
        }
        monthly_inputs = {}
        for month_key, values in monthly_data.items():
            normalized = {}
            for category, amount in _mapping(values, f"monthly_inputs.{month_key}").items():
                category = str(category)
                if category == "other_label":
                    if not isinstance(amount, str):
                        raise RequestValidationError(f"monthly_inputs.{month_key}.other_label must be text.")
                    normalized[category] = amount
                else:
                    normalized[category] = _number(amount, f"monthly_inputs.{month_key}.{category}")
            monthly_inputs[str(month_key)] = normalized

        return cls(
            months=months,
            start_month=start_month,
            starting_cash=_number(data.get("starting_cash"), "starting_cash"),
            apy=_number(data.get("apy"), "apy"),
            recurring=recurring,
            monthly_inputs=monthly_inputs,
            start_year=start_year,
        )

    def to_state(self) -> dict[str, Any]:
        return {
            "months": self.months,
            "start_month": self.start_month,
            "starting_cash": self.starting_cash,
            "apy": self.apy,
            "recurring": self.recurring,
        }


@dataclass(frozen=True)
class SaveCashflowRunRequest:
    """An explicit request to persist server-calculated scenario results."""

    name: str
    notes: str | None
    scenario: CashflowProjectionRequest

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "SaveCashflowRunRequest":
        data = _mapping(payload, "request")
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise RequestValidationError("name is required.")
        if len(name.strip()) > 200:
            raise RequestValidationError("name must be 200 characters or fewer.")
        notes = data.get("notes")
        if notes is not None and not isinstance(notes, str):
            raise RequestValidationError("notes must be text.")
        return cls(
            name=name.strip(),
            notes=notes.strip() if notes and notes.strip() else None,
            scenario=CashflowProjectionRequest.from_mapping(_mapping(data.get("scenario"), "scenario")),
        )


@dataclass(frozen=True)
class VehicleTcoRequest:
    """Validated API request wrapping the deterministic vehicle TCO model."""

    scenario: VehicleTcoScenario

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "VehicleTcoRequest":
        data = _mapping(payload, "request")
        raw_costs = data.get("costs", [])
        if not isinstance(raw_costs, list):
            raise RequestValidationError("costs must be an array.")
        costs = []
        for index, raw_cost in enumerate(raw_costs):
            cost = _mapping(raw_cost, f"costs.{index}")
            try:
                costs.append(
                    OwnershipCost(
                        name=str(cost.get("name", "")),
                        amount=_decimal(cost.get("amount"), f"costs.{index}.amount"),
                        basis=cost.get("basis"),
                    )
                )
            except ValueError as error:
                raise RequestValidationError(str(error)) from error
        try:
            scenario = VehicleTcoScenario(
                vehicle_name=str(data.get("vehicle_name", "")),
                duration_months=int(data.get("duration_months")),
                costs=tuple(costs),
                expected_resale_value=_decimal(data.get("expected_resale_value", 0), "expected_resale_value"),
                starting_odometer=None if data.get("starting_odometer") is None else _decimal(data["starting_odometer"], "starting_odometer"),
                ending_odometer=None if data.get("ending_odometer") is None else _decimal(data["ending_odometer"], "ending_odometer"),
            )
        except (TypeError, ValueError) as error:
            raise RequestValidationError(str(error)) from error
        return cls(scenario)
