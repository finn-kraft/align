import unittest

from backend.align_api.contracts import VehicleTcoRequest
from backend.align_api.errors import RequestValidationError
from backend.align_api.services.tco import calculate_vehicle_tco


class TcoApiCoreTests(unittest.TestCase):
    def test_validates_and_calculates_exact_tco_response(self):
        request = VehicleTcoRequest.from_mapping(
            {
                "vehicle_name": "Jetta",
                "duration_months": 12,
                "costs": [
                    {"name": "fuel", "amount": "1200.25", "basis": "observed"},
                    {"name": "maintenance", "amount": "600", "basis": "assumption"},
                ],
                "expected_resale_value": "500",
                "starting_odometer": "10000",
                "ending_odometer": "20000",
            }
        )
        result = calculate_vehicle_tco(request)

        self.assertEqual(result["observed_cost"], "1200.25")
        self.assertEqual(result["assumed_cost"], "600")
        self.assertEqual(result["net_cost"], "1300.25")
        self.assertEqual(result["miles"], "10000")
        self.assertEqual(result["net_cost_per_mile"], "0.130025")

    def test_rejects_ambiguous_or_invalid_tco_inputs(self):
        with self.assertRaises(RequestValidationError):
            VehicleTcoRequest.from_mapping({"vehicle_name": "Jetta", "duration_months": 12, "costs": {}})
        with self.assertRaises(RequestValidationError):
            VehicleTcoRequest.from_mapping(
                {
                    "vehicle_name": "Jetta",
                    "duration_months": 12,
                    "costs": [{"name": "fuel", "amount": -1, "basis": "observed"}],
                }
            )


if __name__ == "__main__":
    unittest.main()
