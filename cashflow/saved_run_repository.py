"""PostgreSQL persistence for immutable cash-flow saved runs."""

import json
import os
from decimal import Decimal
from typing import Any, Callable

from .saved_runs import SavedRunSnapshot

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
    except ImportError as error:
        raise RuntimeError("Install psycopg to save runs to PostgreSQL.") from error
    return psycopg.connect(url)


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
