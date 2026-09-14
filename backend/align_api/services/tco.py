"""Vehicle TCO API use cases."""

from dataclasses import asdict
from decimal import Decimal
from typing import Any

from vehicles.tco import calculate_tco

from ..contracts import VehicleTcoRequest


def calculate_vehicle_tco(request: VehicleTcoRequest) -> dict[str, Any]:
    """Return exact decimal results in a JSON-safe representation."""

    result = asdict(calculate_tco(request.scenario))
    return {key: _json_value(value) for key, value in result.items()}


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    return value
