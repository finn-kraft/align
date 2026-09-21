import unittest

from cashflow.electricity_integration import (
    TMAX,
    TMIN,
    build_average_weather,
    build_occupancy_schedule,
    validate_occupancy_dates,
)


class ElectricityInputTests(unittest.TestCase):
    def test_weather_uses_seasonal_calendar_day_climatology(self):
        winter = build_average_weather("2026-01-15", "2026-01-15").iloc[0]
        summer = build_average_weather("2026-07-15", "2026-07-15").iloc[0]
        self.assertLess(winter[TMAX], summer[TMAX])
        self.assertLess(winter[TMIN], summer[TMIN])
        self.assertGreater(summer[TMAX] - winter[TMAX], 25)

    def test_weather_repeats_profile_in_future_years(self):
        first = build_average_weather("2026-04-15", "2026-04-15").iloc[0]
        later = build_average_weather("2030-04-15", "2030-04-15").iloc[0]
        self.assertEqual(first[TMAX], later[TMAX])
        self.assertEqual(first[TMIN], later[TMIN])

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
