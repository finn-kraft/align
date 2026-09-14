from decimal import Decimal
import unittest

from vehicles.tco import OwnershipCost, VehicleTcoScenario, calculate_tco


class VehicleTcoTests(unittest.TestCase):
    def test_calculates_observed_and_assumed_costs_separately(self):
        result = calculate_tco(
            VehicleTcoScenario(
                vehicle_name="Current vehicle",
                duration_months=24,
                costs=(
                    OwnershipCost("purchase", Decimal("18000"), "observed"),
                    OwnershipCost("fuel", Decimal("2400"), "observed"),
                    OwnershipCost("future maintenance", Decimal("1200"), "assumption"),
                ),
                expected_resale_value=Decimal("11000"),
                starting_odometer=Decimal("10000"),
                ending_odometer=Decimal("30000"),
            )
        )

        self.assertEqual(result.observed_cost, Decimal("20400"))
        self.assertEqual(result.assumed_cost, Decimal("1200"))
        self.assertEqual(result.gross_cost, Decimal("21600"))
        self.assertEqual(result.net_cost, Decimal("10600"))
        self.assertEqual(result.net_cost_per_month, Decimal("10600") / Decimal("24"))
        self.assertEqual(result.net_cost_per_mile, Decimal("10600") / Decimal("20000"))

    def test_missing_mileage_remains_explicitly_unknown(self):
        result = calculate_tco(
            VehicleTcoScenario("Vehicle", 12, (OwnershipCost("insurance", Decimal("500"), "observed"),))
        )
        self.assertIsNone(result.miles)
        self.assertIsNone(result.net_cost_per_mile)

    def test_rejects_invalid_scenarios(self):
        with self.assertRaisesRegex(ValueError, "ending odometer"):
            VehicleTcoScenario("Vehicle", 12, (), starting_odometer=Decimal("20"), ending_odometer=Decimal("10"))
        with self.assertRaisesRegex(ValueError, "cost amount"):
            OwnershipCost("repair", Decimal("-1"), "observed")


if __name__ == "__main__":
    unittest.main()
