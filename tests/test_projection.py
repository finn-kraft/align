import unittest

from cashflow.projection import generate_month_sequence, run_projection


class ProjectionTests(unittest.TestCase):
    def test_sequence_rolls_over_year_boundary(self):
        self.assertEqual(
            generate_month_sequence("Nov", 3, 2025),
            [
                {"label": "Nov 2025", "key": "2025_11"},
                {"label": "Dec 2025", "key": "2025_12"},
                {"label": "Jan 2026", "key": "2026_01"},
            ],
        )

    def test_projection_matches_existing_float_arithmetic_and_rounding(self):
        state = {
            "months": 2,
            "start_month": "Jan",
            "starting_cash": 1000,
            "apy": 12,
            "recurring": {"rent": 100, "food": 50, "phone": 10, "internet": 40},
        }
        inputs = {
            "2025_01": {
                "income": 500,
                "insurance": 50,
                "utilities": 0,
                "gas": 0,
                "clothing": 0,
                "fun": 0,
                "eating_out": 0,
                "giving": 0,
                "car_repair": 0,
                "other_amount": 0,
            },
            "2025_02": {
                "income": 500,
                "insurance": 100,
                "utilities": 0,
                "gas": 0,
                "clothing": 0,
                "fun": 0,
                "eating_out": 0,
                "giving": 0,
                "car_repair": 0,
                "other_amount": 0,
            },
        }

        self.assertEqual(
            run_projection(state, inputs, start_year=2025),
            [
                {
                    "Month": "Jan 2025",
                    "Income": 500,
                    "Interest Earned": 10.0,
                    "Recurring": 200,
                    "Variable": 50,
                    "Net Change": 260.0,
                    "Ending Balance": 1260.0,
                },
                {
                    "Month": "Feb 2025",
                    "Income": 500,
                    "Interest Earned": 12.6,
                    "Recurring": 200,
                    "Variable": 100,
                    "Net Change": 212.6,
                    "Ending Balance": 1472.6,
                },
            ],
        )

    def test_missing_month_values_retain_zero_default_behavior(self):
        state = {
            "months": 1,
            "start_month": "Jan",
            "starting_cash": 100,
            "apy": 0,
            "recurring": {"rent": 0},
        }
        projection = run_projection(state, {"2025_01": {"income": None}}, start_year=2025)
        self.assertEqual(projection[0]["Ending Balance"], 100.0)
        self.assertEqual(projection[0]["Variable"], 0)


if __name__ == "__main__":
    unittest.main()
