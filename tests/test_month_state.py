import unittest

from cashflow.month_state import ensure_month_defaults


class MonthStateTests(unittest.TestCase):
    def test_existing_typed_values_are_not_replaced(self):
        existing = {"2025_01": {"income": 1234, "gas": 50}}
        updated, changed = ensure_month_defaults(
            existing,
            ["2025_01"],
            lambda: {"income": 0, "gas": 0},
        )

        self.assertFalse(changed)
        self.assertEqual(updated, existing)
        self.assertIsNot(updated, existing)

    def test_only_new_months_receive_defaults(self):
        existing = {"2025_01": {"income": 1234, "gas": 50}}
        updated, changed = ensure_month_defaults(
            existing,
            ["2025_01", "2025_02"],
            lambda: {"income": 0, "gas": 0},
        )

        self.assertTrue(changed)
        self.assertEqual(updated["2025_01"]["income"], 1234)
        self.assertEqual(updated["2025_02"], {"income": 0, "gas": 0})


if __name__ == "__main__":
    unittest.main()
