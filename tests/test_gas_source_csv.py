from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from gas.source_csv import read_gas_source_csv


class GasSourceCsvTests(unittest.TestCase):
    def test_reads_sheet_preamble_and_preserves_physical_line_numbers(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "export.csv"
            path.write_text(
                ",,,,Miles since last fill,Mpg of last tank\n"
                "Timestamp,Odometer,Gallons,Total Cost,Trip Type,Card paid with\n"
                "5/12/2025 23:52:00,82829,11.468,30.72,Regular,Other\n",
                encoding="utf-8",
            )

            source = read_gas_source_csv(path, default_vehicle="Jetta")

            self.assertEqual(source.header_row, 2)
            self.assertEqual(len(source.preamble), 1)
            self.assertEqual(source.rows[0]["__source_row__"], "3")
            self.assertEqual(source.rows[0]["Vehicle"], "Jetta")
            self.assertEqual(source.rows[0]["Trip Type"], "Regular")

    def test_rejects_exports_without_observed_data_headers(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("foo,bar\n1,2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Could not find"):
                read_gas_source_csv(path)


if __name__ == "__main__":
    unittest.main()
