from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.align_api.errors import DataFormatError, DataUnavailableError
from backend.align_api.services.gas import get_gas_dashboard
from gas.pipeline import run_pipeline


class GasApiCoreTests(unittest.TestCase):
    def test_reads_processed_records_and_summary(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "live.csv"
            output = root / "processed.csv"
            source.write_text(
                "Timestamp,Odometer,Gallons,Total Cost\n"
                "2026-01-01,100,10,30\n"
                "2026-01-10,300,8,28\n",
                encoding="utf-8",
            )
            run_pipeline(source, output, root / "rejected.csv", source_name="fixture")

            response = get_gas_dashboard(output)

            self.assertEqual(response["summary"]["record_count"], 1)
            self.assertEqual(response["summary"]["total_cost"], "28")
            self.assertEqual(response["summary"]["total_miles"], "200")
            self.assertEqual(response["summary"]["average_trip_mpg"], "25")
            self.assertEqual(response["summary"]["quality_issue_count"], 0)
            self.assertEqual(response["records"][0]["Source Name"], "fixture")

    def test_reports_missing_or_invalid_derived_data(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(DataUnavailableError):
                get_gas_dashboard(root / "missing.csv")
            invalid = root / "invalid.csv"
            invalid.write_text("Timestamp,Odometer\n2026-01-01,100\n", encoding="utf-8")
            with self.assertRaises(DataFormatError):
                get_gas_dashboard(invalid)


if __name__ == "__main__":
    unittest.main()
