import unittest

from backend.align_api.config import load_settings
from backend.align_api.contracts import CashflowProjectionRequest
from backend.align_api.errors import RequestValidationError
from backend.align_api.services.cashflow import project_cashflow


class ApiCoreTests(unittest.TestCase):
    def test_settings_use_environment_without_connecting(self):
        settings = load_settings({"ALIGN_ENV": "test", "ALIGN_DATABASE_URL": "postgresql://agent@db/align"})
        self.assertEqual(settings.environment, "test")
        self.assertTrue(settings.database_configured)
        self.assertEqual(settings.database_url, "postgresql://agent@db/align")

    def test_settings_allow_database_free_health_runtime(self):
        settings = load_settings({})
        self.assertEqual(settings.app_name, "Align API")
        self.assertFalse(settings.database_configured)

    def test_projection_contract_validates_and_calls_existing_service(self):
        request = CashflowProjectionRequest.from_mapping(
            {
                "months": 1,
                "start_month": "Jan",
                "start_year": 2025,
                "starting_cash": 1000,
                "apy": 12,
                "recurring": {"rent": 100},
                "monthly_inputs": {"2025_01": {"income": 500, "gas": 20}},
            }
        )

        result = project_cashflow(request)
        self.assertEqual(result["model_version"], "cashflow-simulator/v1")
        self.assertEqual(result["projection"][0]["Ending Balance"], 1390.0)

    def test_projection_contract_rejects_invalid_months_and_numbers(self):
        with self.assertRaises(RequestValidationError):
            CashflowProjectionRequest.from_mapping({"months": 1.5})
        with self.assertRaises(RequestValidationError):
            CashflowProjectionRequest.from_mapping(
                {
                    "months": 1,
                    "start_month": "Jan",
                    "starting_cash": float("nan"),
                    "apy": 0,
                }
            )


if __name__ == "__main__":
    unittest.main()
