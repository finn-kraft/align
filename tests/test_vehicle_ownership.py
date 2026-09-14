from datetime import date
from decimal import Decimal
import os
import unittest
from uuid import UUID

from assets.vehicle_ownership import VehicleCostEvent, as_money
from assets.vehicle_repository import create_vehicle, list_vehicles, record_cost_event


class FakeCursor:
    def __init__(self, rows=()):
        self.calls = []
        self.closed = False
        self.rows = rows

    def execute(self, sql, parameters=None):
        self.calls.append((sql, parameters))

    def close(self):
        self.closed = True

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows=()):
        self.cursor_instance = FakeCursor(rows)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class VehicleOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.old_url = os.environ.get("ALIGN_DATABASE_URL")
        os.environ["ALIGN_DATABASE_URL"] = "postgresql://runtime@localhost/align"

    def tearDown(self):
        if self.old_url is None:
            os.environ.pop("ALIGN_DATABASE_URL", None)
        else:
            os.environ["ALIGN_DATABASE_URL"] = self.old_url

    def test_money_and_event_validation(self):
        self.assertEqual(Decimal("12.35"), as_money("12.345"))
        with self.assertRaises(ValueError):
            as_money("-0.01")
        with self.assertRaises(ValueError):
            VehicleCostEvent(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), date(2026, 1, 1), "maintenance", "", Decimal("10"))

    def test_vehicle_purchase_is_an_ownership_cost(self):
        connection = FakeConnection()
        vehicle_id = create_vehicle(name="Jetta", acquired_on=date(2026, 1, 1), purchase_price="5000", starting_odometer="120000", connection_factory=lambda url: connection)
        self.assertEqual(2, len(connection.cursor_instance.calls))
        self.assertEqual(vehicle_id, connection.cursor_instance.calls[1][1][1])
        self.assertEqual("purchase", connection.cursor_instance.calls[1][1][3])
        self.assertTrue(connection.committed)

    def test_saved_vehicle_can_be_loaded_for_display(self):
        vehicle_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        connection = FakeConnection(rows=[(
            vehicle_id, "Jetta", "Volkswagen", "Jetta", 2014,
            date(2026, 1, 1), Decimal("120000"), None,
        )])

        vehicles = list_vehicles(connection_factory=lambda url: connection)

        self.assertEqual(1, len(vehicles))
        self.assertEqual(vehicle_id, vehicles[0].id)
        self.assertEqual("Jetta", vehicles[0].name)

    def test_maintenance_and_repairs_are_recorded_as_distinct_categories(self):
        connection = FakeConnection()
        event = VehicleCostEvent(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), date(2026, 2, 1), "maintenance", "Oil change", "54.95", odometer="121000")
        record_cost_event(event, connection_factory=lambda url: connection)
        params = connection.cursor_instance.calls[0][1]
        self.assertEqual("maintenance", params[3])
        self.assertEqual("Oil change", params[4])
        self.assertEqual(Decimal("54.95"), params[6])


if __name__ == "__main__":
    unittest.main()
