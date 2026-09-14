"""Validated, framework-independent contracts for Align's public API."""

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping

from cashflow.projection import MONTHS

from .errors import RequestValidationError


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
        monthly_inputs = {
            str(month_key): {
                str(category): _number(amount, f"monthly_inputs.{month_key}.{category}")
                for category, amount in _mapping(values, f"monthly_inputs.{month_key}").items()
            }
            for month_key, values in monthly_data.items()
        }

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
