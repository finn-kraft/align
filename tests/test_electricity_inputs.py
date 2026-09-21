import unittest

from cashflow.electricity_integration import (
    AVERAGE_TMAX_F,
    AVERAGE_TMIN_F,
    build_average_weather,
    build_occupancy_schedule,
    validate_occupancy_dates,
)


class ElectricityInputTests(unittest.TestCase):
    def test_weather_uses_hardcoded_temperature_means(self):
        weather = build_average_weather("2026-01-01", "2026-01-03")
        self.assertEqual(len(weather), 3)
        self.assertTrue((weather["TMAX (Degrees Fahrenheit)"] == AVERAGE_TMAX_F).all())
        self.assertTrue((weather["TMIN (Degrees Fahrenheit)"] == AVERAGE_TMIN_F).all())

    def test_occupancy_date_range(self):
        schedule = build_occupancy_schedule(
            "2026-01-01", "2026-01-05", "2026-01-03", "2026-01-04"
        )
        self.assertEqual(schedule["Occupied"].tolist(), [0, 0, 1, 1, 0])

    def test_reversed_occupancy_dates_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_occupancy_dates("2026-02-01", "2026-01-01")


if __name__ == "__main__":
    unittest.main()
