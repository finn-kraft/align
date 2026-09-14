"""Cash-flow API use cases backed by the canonical Python projection service."""

from typing import Any, Callable

from cashflow.projection import run_projection
from cashflow.saved_run_repository import get_saved_run, list_saved_runs, save_run
from cashflow.saved_runs import PersistedSavedRun, SavedRunSnapshot, SavedRunSummary, build_saved_run_snapshot

from ..contracts import CashflowProjectionRequest, SaveCashflowRunRequest


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


def save_cashflow_run(
    request: SaveCashflowRunRequest,
    *,
    writer: Callable[[SavedRunSnapshot], None] = save_run,
) -> SavedRunSnapshot:
    """Calculate results server-side, then explicitly persist one immutable run."""
    projection = project_cashflow(request.scenario)["projection"]
    snapshot = build_saved_run_snapshot(
        name=request.name,
        notes=request.notes,
        state=request.scenario.to_state(),
        monthly_inputs=request.scenario.monthly_inputs,
        projection=projection,
    )
    writer(snapshot)
    return snapshot


def list_cashflow_runs(
    *,
    limit: int = 50,
    offset: int = 0,
    reader: Callable[..., tuple[SavedRunSummary, ...]] = list_saved_runs,
) -> tuple[SavedRunSummary, ...]:
    """Read saved-run metadata without recalculating historical scenarios."""
    return reader(limit=limit, offset=offset)


def get_cashflow_run(
    run_id,
    *,
    reader: Callable[..., PersistedSavedRun | None] = get_saved_run,
) -> PersistedSavedRun | None:
    """Read the immutable stored snapshot, including persisted monthly results."""
    return reader(run_id)
