import unittest

import pandas as pd

from cashflow.electricity_integration import (
    forecast_to_cashflow_months,
    merge_electricity_into_month_inputs,
)


class ElectricityIntegrationTests(unittest.TestCase):
    def test_forecast_maps_predicted_bills_to_monthly_utilities(self):
        rows = pd.DataFrame(
            {
                "Billing From": ["2026-10-01", "2026-10-20", "2026-11-01"],
                "Predicted Bill": [101.234, 20.0, 88.5],
            }
        )
        self.assertEqual(
            forecast_to_cashflow_months(rows),
            {
                "2026_10": {"utilities": 121.23},
                "2026_11": {"utilities": 88.50},
            },
        )

    def test_merge_preserves_other_cashflow_fields(self):
        monthly = {"2026_10": {"income": 2000, "utilities": 50, "gas": 100}}
        merged = merge_electricity_into_month_inputs(
            monthly, {"2026_10": {"utilities": 121.23}}
        )
        self.assertEqual(merged["2026_10"]["income"], 2000)
        self.assertEqual(merged["2026_10"]["gas"], 100)
        self.assertEqual(merged["2026_10"]["utilities"], 121.23)


if __name__ == "__main__":
    unittest.main()
