"""Reusable time-series helpers for gas analytics."""

from __future__ import annotations

import pandas as pd


def rolling_average(values, *, window: int = 5) -> pd.Series:
    """Return an aligned rolling mean while retaining gaps in observed data."""

    if not isinstance(window, int) or isinstance(window, bool) or window < 1:
        raise ValueError("window must be a positive integer.")
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.rolling(window=window, min_periods=1).mean()
