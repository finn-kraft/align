"""Cash-flow API use cases backed by the canonical Python projection service."""

from typing import Any

from cashflow.projection import run_projection

from ..contracts import CashflowProjectionRequest


def project_cashflow(request: CashflowProjectionRequest) -> dict[str, Any]:
    """Calculate a projection without involving UI or persistence code."""
    return {
        "model_version": "cashflow-simulator/v1",
        "projection": run_projection(
            request.to_state(),
            request.monthly_inputs,
            start_year=request.start_year,
        ),
    }
