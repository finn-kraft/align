import ast
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryEntrypointTests(unittest.TestCase):
    def test_gas_dashboard_is_valid_python(self):
        ast.parse((ROOT / "gas" / "gas_dashboard.py").read_text(encoding="utf-8"))

    def test_launcher_is_valid_shell(self):
        result = subprocess.run(
            ["bash", "-n", str(ROOT / "run")],
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
