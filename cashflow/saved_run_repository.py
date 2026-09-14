"""PostgreSQL persistence for immutable cash-flow saved runs."""

import json
import os
from decimal import Decimal
from typing import Any, Callable

from .saved_runs import (
    PersistedSavedRun,
    SavedRunMonth,
    SavedRunSnapshot,
    SavedRunSummary,
)


RUN_INSERT = """
INSERT INTO cashflow_saved_runs
    (id, model_version, name, notes, start_date, month_count, starting_cash,
     apy, assumptions)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
"""

MONTH_INSERT = """
INSERT INTO cashflow_saved_run_months
    (saved_run_id, month_index, month_start, income, interest_income,
     recurring_expense, variable_expense, net_change, ending_cash,
     expense_categories)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
"""

RUN_LIST_QUERY = """
SELECT id, created_at, model_version, name, notes, start_date, month_count,
       starting_cash, apy
FROM cashflow_saved_runs
ORDER BY created_at DESC, id DESC
LIMIT %s OFFSET %s
"""

RUN_DETAIL_QUERY = """
SELECT id, created_at, model_version, name, notes, start_date, month_count,
       starting_cash, apy, assumptions
FROM cashflow_saved_runs
WHERE id = %s
"""

RUN_MONTHS_QUERY = """
SELECT month_index, month_start, income, interest_income, recurring_expense,
       variable_expense, net_change, ending_cash, expense_categories
FROM cashflow_saved_run_months
WHERE saved_run_id = %s
ORDER BY month_index ASC
"""


def _json_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Cannot encode {type(value).__name__} as JSON.")


def database_url() -> str:
    """Return the required database URL without accepting inline credentials."""
    url = os.environ.get("ALIGN_DATABASE_URL")
    if not url:
        raise RuntimeError("ALIGN_DATABASE_URL must be set before saving a run.")
    return url


def default_connection_factory(url: str):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Install psycopg to save runs to PostgreSQL.") from error
    return psycopg.connect(url, row_factory=dict_row)


def _row_value(row: Any, key: str, position: int) -> Any:
    return row[key] if isinstance(row, dict) else row[position]


def _summary_from_row(row: Any) -> SavedRunSummary:
    return SavedRunSummary(
        id=_row_value(row, "id", 0),
        created_at=_row_value(row, "created_at", 1),
        model_version=_row_value(row, "model_version", 2),
        name=_row_value(row, "name", 3),
        notes=_row_value(row, "notes", 4),
        start_date=_row_value(row, "start_date", 5),
        month_count=_row_value(row, "month_count", 6),
        starting_cash=_row_value(row, "starting_cash", 7),
        apy=_row_value(row, "apy", 8),
    )


def _month_from_row(row: Any) -> SavedRunMonth:
    return SavedRunMonth(
        month_index=_row_value(row, "month_index", 0),
        month_start=_row_value(row, "month_start", 1),
        income=_row_value(row, "income", 2),
        interest_income=_row_value(row, "interest_income", 3),
        recurring_expense=_row_value(row, "recurring_expense", 4),
        variable_expense=_row_value(row, "variable_expense", 5),
        net_change=_row_value(row, "net_change", 6),
        ending_cash=_row_value(row, "ending_cash", 7),
        expense_categories=_row_value(row, "expense_categories", 8),
    )


def _validate_pagination(limit: int, offset: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer from 1 through 100.")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("offset must be a non-negative integer.")


def save_run(
    snapshot: SavedRunSnapshot,
    connection_factory: Callable[[str], Any] = default_connection_factory,
) -> None:
    """Insert a run and all monthly snapshots atomically."""
    connection = connection_factory(database_url())
    cursor = connection.cursor()
    try:
        cursor.execute(
            RUN_INSERT,
            (
                snapshot.id,
                snapshot.model_version,
                snapshot.name,
                snapshot.notes,
                snapshot.start_date,
                snapshot.month_count,
                snapshot.starting_cash,
                snapshot.apy,
                json.dumps(snapshot.assumptions, default=_json_default),
            ),
        )
        cursor.executemany(
            MONTH_INSERT,
            [
                (
                    snapshot.id,
                    month.month_index,
                    month.month_start,
                    month.income,
                    month.interest_income,
                    month.recurring_expense,
                    month.variable_expense,
                    month.net_change,
                    month.ending_cash,
                    json.dumps(month.expense_categories, default=_json_default),
                )
                for month in snapshot.months
            ],
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def list_saved_runs(
    *,
    limit: int = 50,
    offset: int = 0,
    connection_factory: Callable[[str], Any] = default_connection_factory,
) -> tuple[SavedRunSummary, ...]:
    """Return immutable run metadata newest first without reading calculations."""
    _validate_pagination(limit, offset)
    connection = connection_factory(database_url())
    cursor = connection.cursor()
    try:
        cursor.execute(RUN_LIST_QUERY, (limit, offset))
        return tuple(_summary_from_row(row) for row in cursor.fetchall())
    finally:
        cursor.close()
        connection.close()


def get_saved_run(
    run_id,
    *,
    connection_factory: Callable[[str], Any] = default_connection_factory,
) -> PersistedSavedRun | None:
    """Return the stored snapshot and ordered results without recalculation."""
    connection = connection_factory(database_url())
    cursor = connection.cursor()
    try:
        cursor.execute(RUN_DETAIL_QUERY, (run_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        summary = _summary_from_row(row)
        assumptions = _row_value(row, "assumptions", 9)
        cursor.execute(RUN_MONTHS_QUERY, (run_id,))
        months = tuple(_month_from_row(month) for month in cursor.fetchall())
        return PersistedSavedRun(summary=summary, assumptions=assumptions, months=months)
    finally:
        cursor.close()
        connection.close()
