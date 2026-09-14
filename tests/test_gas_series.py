import math
import unittest

import pandas as pd

from gas.series import rolling_average


class GasSeriesTests(unittest.TestCase):
    def test_five_observation_rolling_average(self):
        result = rolling_average(pd.Series([10, 20, 30, 40, 50, 60]), window=5)

        self.assertEqual(result.tolist(), [10, 15, 20, 25, 30, 40])

    def test_invalid_values_remain_gaps_without_breaking_later_average(self):
        result = rolling_average(pd.Series([20, None, 40]), window=5)

        self.assertEqual(result.iloc[0], 20)
        self.assertTrue(math.isnan(result.iloc[1]))
        self.assertEqual(result.iloc[2], 30)

    def test_window_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "positive integer"):
            rolling_average(pd.Series([1, 2]), window=0)


if __name__ == "__main__":
    unittest.main()
