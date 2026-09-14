"""Fixed-query PostgreSQL persistence for vehicle ownership records."""

import os
from decimal import Decimal
from typing import Any, Callable
from uuid import UUID, uuid4

from .vehicle_ownership import Vehicle, VehicleCostEvent, VehicleOwnershipSummary, as_money


INSERT_VEHICLE = """
INSERT INTO vehicles (id, name, make, model, year, acquired_on, starting_odometer)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""
INSERT_COST_EVENT = """
INSERT INTO vehicle_cost_events
    (id, vehicle_id, occurred_on, cost_category, service_type, description, amount, odometer, notes)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
LIST_VEHICLES = """
SELECT id, name, make, model, year, acquired_on, starting_odometer, created_at
FROM vehicles
ORDER BY acquired_on DESC, name ASC
"""
OWNERSHIP_SUMMARY = """
SELECT v.id AS vehicle_id, v.name AS vehicle_name,
       COALESCE(SUM(e.amount), 0) AS total_cost,
       COALESCE(SUM(e.amount) FILTER (WHERE e.cost_category = 'purchase'), 0) AS purchase_cost,
       COALESCE(SUM(e.amount) FILTER (WHERE e.cost_category = 'maintenance'), 0) AS maintenance_cost,
       COALESCE(SUM(e.amount) FILTER (WHERE e.cost_category = 'repair'), 0) AS repair_cost,
       COALESCE(SUM(e.amount) FILTER (WHERE e.cost_category = 'administrative'), 0) AS administrative_cost,
       COALESCE(SUM(e.amount) FILTER (WHERE e.cost_category = 'fuel'), 0) AS fuel_cost,
       COALESCE(SUM(e.amount) FILTER (WHERE e.cost_category = 'other'), 0) AS other_cost,
       COUNT(e.id) AS event_count
FROM vehicles v
LEFT JOIN vehicle_cost_events e ON e.vehicle_id = v.id
GROUP BY v.id, v.name
ORDER BY v.name ASC
"""
MAINTENANCE_BREAKDOWN = """
SELECT service_type, COUNT(*) AS event_count, SUM(amount) AS total_cost
FROM vehicle_cost_events
WHERE vehicle_id = %s AND cost_category = 'maintenance'
GROUP BY service_type
ORDER BY total_cost DESC, service_type ASC
"""
RECENT_REPAIRS = """
SELECT occurred_on, service_type, description, amount, odometer, notes
FROM vehicle_cost_events
WHERE vehicle_id = %s AND cost_category = 'repair'
ORDER BY occurred_on DESC, id DESC
LIMIT %s
"""


def database_url() -> str:
    """Require a dedicated runtime database URL from the environment."""
    url = os.getenv("ALIGN_DATABASE_URL")
    if not url:
        raise RuntimeError("ALIGN_DATABASE_URL must be set before using Asset Modeling.")
    return url


def default_connection_factory(url: str):
    """Create the optional psycopg connection only when persistence is used."""
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Install project dependencies with ./run install.") from error
    return psycopg.connect(url, row_factory=dict_row)


def _value(row: Any, key: str, index: int) -> Any:
    return row[key] if isinstance(row, dict) else row[index]


def _close(connection: Any, cursor: Any) -> None:
    cursor.close()
    connection.close()


def create_vehicle(
    *,
    name: str,
    acquired_on,
    purchase_price: Decimal | int | float | str = 0,
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    starting_odometer: Decimal | int | float | str | None = None,
    connection_factory: Callable[[str], Any] = default_connection_factory,
) -> UUID:
    """Create a vehicle and, when supplied, its immutable acquisition cost."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Vehicle name is required.")
    if year is not None and not 1886 <= int(year) <= 9999:
        raise ValueError("Vehicle year must be realistic.")
    if starting_odometer is not None and Decimal(str(starting_odometer)) < 0:
        raise ValueError("Starting odometer cannot be negative.")
    vehicle_id = uuid4()
    price = as_money(purchase_price)
    connection = connection_factory(database_url())
    cursor = connection.cursor()
    try:
        cursor.execute(INSERT_VEHICLE, (vehicle_id, normalized_name, make or None, model or None, year, acquired_on, starting_odometer))
        if price:
            cursor.execute(
                INSERT_COST_EVENT,
                (uuid4(), vehicle_id, acquired_on, "purchase", "Vehicle purchase", normalized_name, price, starting_odometer, None),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        _close(connection, cursor)
    return vehicle_id


def record_cost_event(
    event: VehicleCostEvent,
    connection_factory: Callable[[str], Any] = default_connection_factory,
) -> UUID:
    """Insert one immutable maintenance, repair, administrative, or other cost."""
    event_id = event.id or uuid4()
    connection = connection_factory(database_url())
    cursor = connection.cursor()
    try:
        cursor.execute(
            INSERT_COST_EVENT,
            (event_id, event.vehicle_id, event.occurred_on, event.category, event.service_type.strip(), event.description or None, event.amount, event.odometer, event.notes or None),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        _close(connection, cursor)
    return event_id


def list_vehicles(connection_factory: Callable[[str], Any] = default_connection_factory) -> tuple[Vehicle, ...]:
    """Return selectable vehicles without their cost details."""
    connection = connection_factory(database_url())
    cursor = connection.cursor()
    try:
        cursor.execute(LIST_VEHICLES)
        return tuple(
            Vehicle(_value(row, "id", 0), _value(row, "name", 1), _value(row, "make", 2), _value(row, "model", 3), _value(row, "year", 4), _value(row, "acquired_on", 5), _value(row, "starting_odometer", 6), _value(row, "created_at", 7))
            for row in cursor.fetchall()
        )
    finally:
        _close(connection, cursor)


def ownership_summaries(connection_factory: Callable[[str], Any] = default_connection_factory) -> tuple[VehicleOwnershipSummary, ...]:
    """Return total ownership cost and its major category breakdown by vehicle."""
    connection = connection_factory(database_url())
    cursor = connection.cursor()
    try:
        cursor.execute(OWNERSHIP_SUMMARY)
        return tuple(
            VehicleOwnershipSummary(
                _value(row, "vehicle_id", 0), _value(row, "vehicle_name", 1),
                as_money(_value(row, "total_cost", 2)), as_money(_value(row, "purchase_cost", 3)),
                as_money(_value(row, "maintenance_cost", 4)), as_money(_value(row, "repair_cost", 5)),
                as_money(_value(row, "administrative_cost", 6)), as_money(_value(row, "fuel_cost", 7)),
                as_money(_value(row, "other_cost", 8)), _value(row, "event_count", 9),
            ) for row in cursor.fetchall()
        )
    finally:
        _close(connection, cursor)


def maintenance_breakdown(vehicle_id: UUID, connection_factory: Callable[[str], Any] = default_connection_factory) -> tuple[dict[str, Any], ...]:
    """Break maintenance down by individual service type, such as oil changes."""
    connection = connection_factory(database_url())
    cursor = connection.cursor()
    try:
        cursor.execute(MAINTENANCE_BREAKDOWN, (vehicle_id,))
        return tuple({"Service": _value(row, "service_type", 0), "Events": _value(row, "event_count", 1), "Total cost": as_money(_value(row, "total_cost", 2))} for row in cursor.fetchall())
    finally:
        _close(connection, cursor)


def recent_repairs(vehicle_id: UUID, limit: int = 25, connection_factory: Callable[[str], Any] = default_connection_factory) -> tuple[dict[str, Any], ...]:
    """Return repairs separately from routine maintenance for review."""
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer from 1 through 100.")
    connection = connection_factory(database_url())
    cursor = connection.cursor()
    try:
        cursor.execute(RECENT_REPAIRS, (vehicle_id, limit))
        return tuple({"Date": _value(row, "occurred_on", 0), "Repair": _value(row, "service_type", 1), "Description": _value(row, "description", 2), "Amount": as_money(_value(row, "amount", 3)), "Odometer": _value(row, "odometer", 4), "Notes": _value(row, "notes", 5)} for row in cursor.fetchall())
    finally:
        _close(connection, cursor)
