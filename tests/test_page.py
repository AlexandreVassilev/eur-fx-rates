"""Tests for the web page's JavaScript (app.js).

Runs tests/page_tests.js in Apple's JavaScript engine (the one inside Safari)
through the built-in macOS command `osascript`, then checks:
- the small JavaScript checks all pass,
- the CSV the page downloads is byte-for-byte what export_csv.py produces,
  for several ranges, and identical to the September 2026 reference file.
Skipped on computers without osascript (not a Mac). Needs data/export_all.csv
(run update.py first). To run the same checks in a browser, open
http://localhost:8000/tests/page_test.html with the local server running.
"""

import datetime as dt
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from fxrates import export, history, settings as settings_file

PROJECT = Path(__file__).parent.parent
REFERENCE = PROJECT / "tests" / "september_2026_reference.csv"
RANGES = [
    ("2026-09-01", "2026-09-30"),  # the reference month
    ("2025-01-01", "2025-01-01"),  # first day of the history, a single day
    ("2025-02-01", "2025-03-31"),  # crosses a month end, includes 28 February
    ("2026-09-05", "2026-09-06"),  # a weekend: only COP has rates
]


@unittest.skipUnless(shutil.which("osascript"), "osascript not available (not a Mac)")
class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        command = ["osascript", "-l", "JavaScript", str(PROJECT / "tests" / "page_tests_mac.js"), str(PROJECT),
                   *(f"{start}_{end}" for start, end in RANGES)]
        output = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=60, check=True)
        cls.results = json.loads(output.stdout)

    def test_javascript_checks_pass(self):
        self.assertEqual(self.results["failures"], [])

    def test_download_is_byte_for_byte_export_csv(self):
        rates, settings = history.load(), settings_file.load()
        for start, end in RANGES:
            with self.subTest(range=f"{start} to {end}"):
                expected = export.to_csv(rates, dt.date.fromisoformat(start), dt.date.fromisoformat(end), settings)
                self.assertEqual(self.results["downloads"][f"{start}_{end}"].encode("utf-8"), expected.encode("utf-8"))

    def test_september_download_equals_reference_file(self):
        downloaded = self.results["downloads"]["2026-09-01_2026-09-30"].encode("utf-8")
        self.assertEqual(downloaded, REFERENCE.read_bytes())


if __name__ == "__main__":
    unittest.main()
