import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from gas.pipeline import build_gas_analytics, ensure_processed_data, run_pipeline
from gas import process_data


class GasPipelineTests(unittest.TestCase):
    def test_builds_dashboard_metrics_from_validated_rows(self):
        result = build_gas_analytics(
            [
                {"Timestamp": "2026-01-01", "Odometer": "100", "Gallons": "10", "Total Cost": "30"},
                {"Timestamp": "2026-01-10", "Odometer": "300", "Gallons": "8", "Total Cost": "28"},
            ],
            source_name="sheet",
        )

        self.assertEqual(len(result.analytics_rows), 1)
        row = result.analytics_rows[0]
        self.assertEqual(row["MilesPerTank"], "200")
        self.assertEqual(row["TripMPG"], "25")
        self.assertEqual(row["PricePerGallon"], "3.5")
        self.assertEqual(row["CostPerMile"], "0.14")
        self.assertEqual(row["Month"], "2026-01")
        self.assertEqual(row["Data Quality"], "ok")

    def test_flags_missing_intervals_and_bad_prices_without_inventing_corrections(self):
        result = build_gas_analytics(
            [
                {"Timestamp": "2026-01-01", "Odometer": "100", "Gallons": "10", "Total Cost": "30"},
                {"Timestamp": "2026-02-01", "Odometer": "1100", "Gallons": "10", "Total Cost": "120", "Trip Type": "Missing data from previous tanks"},
            ],
            source_name="sheet",
        )
        row = result.analytics_rows[0]
        self.assertEqual(row["TripMPG"], "100")
        self.assertEqual(row["TripMPG_clean"], "")
        self.assertEqual(row["CostPerMile"], "")
        self.assertIn("missing_fills", row["Quality Flags"])
        self.assertIn("implausible_price", row["Quality Flags"])
        self.assertGreaterEqual(len(result.quality_issues), 3)

    def test_retains_plausible_metrics_for_explicitly_aggregated_fills(self):
        result = build_gas_analytics(
            [
                {"Timestamp": "2026-01-01", "Odometer": "100", "Gallons": "10", "Total Cost": "30"},
                {"Timestamp": "2026-02-01", "Odometer": "1100", "Gallons": "32", "Total Cost": "100"},
            ],
            source_name="sheet",
        )
        row = result.analytics_rows[0]
        self.assertEqual(row["TripMPG_clean"], "31.25")
        self.assertEqual(row["Data Quality"], "warning")
        self.assertEqual(row["Quality Flags"], "aggregated_fills")

    def test_pipeline_writes_analytics_and_rejections_without_overwriting_source(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "live_data.csv"
            source.write_text("Timestamp,Odometer,Gallons,Total Cost\n2026-01-01,100,10,30\n2026-01-10,100,8,28\n", encoding="utf-8")
            output = root / "processed_data.csv"
            rejected = root / "rejected_rows.csv"

            result = run_pipeline(source, output, rejected, source_name="google-sheet:jetta")

            self.assertEqual(result.analytics_rows, ())
            self.assertTrue(output.exists())
            self.assertTrue(rejected.exists())
            self.assertIn("odometer must increase", rejected.read_text(encoding="utf-8"))
            with source.open(encoding="utf-8") as source_file:
                self.assertEqual(len(list(csv.DictReader(source_file))), 2)

    def test_legacy_processing_command_targets_the_pipeline_files(self):
        self.assertEqual(process_data.INPUT_FILE.name, "live_data.csv")
        self.assertEqual(process_data.OUTPUT_FILE.name, "processed_data.csv")
        self.assertEqual(process_data.REJECTED_FILE.name, "rejected_rows.csv")


    def test_prepares_dashboard_data_when_source_is_newer(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "live_data.csv"
            output = root / "processed_data.csv"
            rejected = root / "rejected_rows.csv"
            source.write_text(
                "Timestamp,Odometer,Gallons,Total Cost\\n"
                "2026-01-01,100,10,30\\n"
                "2026-01-10,300,8,28\\n",
                encoding="utf-8",
            )

            refreshed = ensure_processed_data(
                source, output, rejected, source_name="local:gas", default_vehicle="Jetta"
            )

            self.assertTrue(refreshed)
            self.assertIn("TripMPG_clean", output.read_text(encoding="utf-8"))
            self.assertFalse(
                ensure_processed_data(
                    source, output, rejected, source_name="local:gas", default_vehicle="Jetta"
                )
            )

    def test_missing_source_is_explicit(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(FileNotFoundError, "No gas source file found"):
                ensure_processed_data(
                    root / "missing.csv",
                    root / "processed.csv",
                    root / "rejected.csv",
                    source_name="local:gas",
                )


if __name__ == "__main__":
    unittest.main()
