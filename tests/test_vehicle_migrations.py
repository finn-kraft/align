from pathlib import Path
import unittest


MIGRATIONS = Path(__file__).resolve().parents[1] / "db" / "migrations"


class VehicleMigrationTests(unittest.TestCase):
    def test_audit_migration_has_no_hard_coded_runtime_role(self):
        migration = (MIGRATIONS / "0003_vehicle_record_management.sql").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("TO align_app", migration)

    def test_runtime_grants_are_complete_and_role_parameterized(self):
        migration = (MIGRATIONS / "0004_grant_vehicle_runtime_permissions.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn('TO :"align_runtime_role"', migration)
        self.assertIn("SELECT, INSERT, UPDATE, DELETE", migration)
        self.assertIn("vehicle_record_audit", migration)


if __name__ == "__main__":
    unittest.main()
