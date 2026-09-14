from decimal import Decimal
import unittest

from gas.normalization import normalize_gas_rows


class GasNormalizationTests(unittest.TestCase):
    def test_normalizes_observed_rows_and_preserves_traceability(self):
        result = normalize_gas_rows(
            [
                {
                    "Date": "2026-03-01 12:30:00",
                    "Mileage": "45,123",
                    "Gallons": "10.25",
                    "Amount": "$34.50",
                    "Vehicle": "Jetta",
                    "Station": "Example Fuel",
                    "Notes": "  regular  ",
                }
            ],
            source_name="google-sheet:jetta",
        )

        self.assertEqual(result.rejected_rows, ())
        entry = result.entries[0]
        self.assertEqual(entry.odometer, Decimal("45123"))
        self.assertEqual(entry.gallons, Decimal("10.25"))
        self.assertEqual(entry.total_cost, Decimal("34.50"))
        self.assertEqual(entry.vehicle, "Jetta")
        self.assertEqual(entry.notes, "regular")
        self.assertEqual(entry.source_name, "google-sheet:jetta")
        self.assertEqual(entry.source_row, 1)
        self.assertEqual(entry.raw_source["Amount"], "$34.50")
        self.assertEqual(len(entry.source_fingerprint), 64)

    def test_rejects_invalid_rows_and_duplicates_without_silent_loss(self):
        valid = {
            "Timestamp": "2026-03-01T12:30:00",
            "Odometer": "45123",
            "Gallons": "10.25",
            "Total Cost": "34.50",
        }
        result = normalize_gas_rows(
            [valid, dict(valid), {"Timestamp": "not-a-date", "Odometer": 3, "Gallons": 0, "Total Cost": 1}],
            source_name="sheet",
        )

        self.assertEqual(len(result.entries), 1)
        self.assertEqual(len(result.rejected_rows), 2)
        self.assertEqual(result.rejected_rows[0].reason, "duplicate observed fuel purchase")
        self.assertEqual(result.rejected_rows[1].reason, "timestamp is malformed")

    def test_requires_all_observed_measurements(self):
        result = normalize_gas_rows(
            [{"Timestamp": "2026/03/01", "Odometer": "", "Gallons": "4", "Total Cost": "9"}],
            source_name="sheet",
        )

        self.assertEqual(result.entries, ())
        self.assertEqual(result.rejected_rows[0].reason, "odometer is required")


if __name__ == "__main__":
    unittest.main()
