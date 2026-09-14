import os
import unittest
from decimal import Decimal
from uuid import UUID

from cashflow.saved_run_repository import save_run
from cashflow.saved_runs import build_saved_run_snapshot


STATE = {
    "months": 2,
    "starting_cash": 1000,
    "apy": 3.3,
    "recurring": {"rent": 750, "food": 400},
}
MONTHLY_INPUTS = {
    "2026_01": {"income": 2000, "gas": 75, "other_label": "Trip", "other_amount": 30},
    "2026_02": {"income": 2100, "gas": 80, "other_label": "", "other_amount": 0},
}
PROJECTION = [
    {"Month": "Jan 2026", "Income": 2000, "Interest Earned": 2.75, "Recurring": 1150, "Variable": 105, "Net Change": 747.75, "Ending Balance": 1747.75},
    {"Month": "Feb 2026", "Income": 2100, "Interest Earned": 4.81, "Recurring": 1150, "Variable": 80, "Net Change": 874.81, "Ending Balance": 2622.56},
]


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.many = []
        self.closed = False

    def execute(self, sql, params):
        self.executed.append((sql, params))

    def executemany(self, sql, params):
        self.many.append((sql, params))

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
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


class SavedRunTests(unittest.TestCase):
    def test_snapshot_preserves_inputs_and_dynamic_categories(self):
        snapshot = build_saved_run_snapshot(
            name=" January plan ",
            notes="  Conservative case ",
            state=STATE,
            monthly_inputs=MONTHLY_INPUTS,
            projection=PROJECTION,
            run_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        )

        self.assertEqual(snapshot.name, "January plan")
        self.assertEqual(snapshot.notes, "Conservative case")
        self.assertEqual(str(snapshot.start_date), "2026-01-01")
        self.assertEqual(snapshot.months[0].expense_categories["gas"], Decimal("75.00"))
        self.assertEqual(snapshot.months[0].expense_categories["other"]["label"], "Trip")
        self.assertEqual(snapshot.assumptions["monthly_inputs"], MONTHLY_INPUTS)

    def test_snapshot_requires_a_name_and_matching_projection(self):
        with self.assertRaises(ValueError):
            build_saved_run_snapshot(name="", notes=None, state=STATE, monthly_inputs=MONTHLY_INPUTS, projection=PROJECTION)
        with self.assertRaises(ValueError):
            build_saved_run_snapshot(name="Test", notes=None, state=STATE, monthly_inputs=MONTHLY_INPUTS, projection=PROJECTION[:1])

    def test_repository_uses_environment_url_and_commits_atomically(self):
        snapshot = build_saved_run_snapshot(name="Test", notes=None, state=STATE, monthly_inputs=MONTHLY_INPUTS, projection=PROJECTION)
        connection = FakeConnection()
        old_url = os.environ.get("ALIGN_DATABASE_URL")
        os.environ["ALIGN_DATABASE_URL"] = "postgresql://runtime-role@localhost/align"
        try:
            save_run(snapshot, connection_factory=lambda url: connection)
        finally:
            if old_url is None:
                os.environ.pop("ALIGN_DATABASE_URL", None)
            else:
                os.environ["ALIGN_DATABASE_URL"] = old_url

        self.assertTrue(connection.committed)
        self.assertFalse(connection.rolled_back)
        self.assertEqual(len(connection.cursor_instance.executed), 1)
        self.assertEqual(len(connection.cursor_instance.many[0][1]), 2)
        self.assertTrue(connection.closed)

    def test_repository_rejects_missing_environment_url(self):
        old_url = os.environ.pop("ALIGN_DATABASE_URL", None)
        try:
            snapshot = build_saved_run_snapshot(name="Test", notes=None, state=STATE, monthly_inputs=MONTHLY_INPUTS, projection=PROJECTION)
            with self.assertRaises(RuntimeError):
                save_run(snapshot, connection_factory=lambda url: FakeConnection())
        finally:
            if old_url is not None:
                os.environ["ALIGN_DATABASE_URL"] = old_url


if __name__ == "__main__":
    unittest.main()
