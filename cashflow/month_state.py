"""State helpers for rendering cash-flow month input cards."""

from copy import deepcopy
from typing import Any, Callable, Mapping


def ensure_month_defaults(
    existing: Mapping[str, Mapping[str, Any]],
    month_keys: list[str],
    default_factory: Callable[[], dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], bool]:
    """Add cards for newly selected months without rewriting typed values.

    Call this only when the selected month range changes. Calling it for every
    numeric input update would replace Shiny's rendered input elements and
    discard browser focus.
    """
    updated = deepcopy(dict(existing))
    changed = False
    for key in month_keys:
        if key not in updated:
            updated[key] = default_factory()
            changed = True
    return updated, changed
