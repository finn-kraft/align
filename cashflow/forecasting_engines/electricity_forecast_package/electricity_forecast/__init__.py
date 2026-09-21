"""Import bridge for the repository's hyphenated forecast package."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

_SOURCE = (
    Path(__file__).resolve().parents[3]
    / "forecasting-engines"
    / "electricity_forecast_package"
    / "electricity_forecast"
    / "core.py"
)
_spec = spec_from_file_location("align_electricity_forecast_core", _SOURCE)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Unable to load electricity forecaster from {_SOURCE}")
_module = module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)

ElectricityForecaster = _module.ElectricityForecaster
Tariff = _module.Tariff

__all__ = ["ElectricityForecaster", "Tariff"]
