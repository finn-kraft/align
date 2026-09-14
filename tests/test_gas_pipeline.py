import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from gas.pipeline import build_gas_analytics, run_pipeline
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


if __name__ == "__main__":
    unittest.main()
