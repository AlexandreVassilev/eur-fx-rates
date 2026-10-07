"""Live test: fetch September 2026 from all four central banks and compare
every cell with the hand-made reference file. Needs an internet connection
and takes about a minute (the UAE source needs one request per day).

Run from the project folder with:  python3 -m unittest tests.test_september_2026 -v
"""

import datetime as dt
import unittest
from pathlib import Path

from fxrates import argentina, banque_de_france, colombia, export, settings, uae

REFERENCE = Path(__file__).parent / "september_2026_reference.csv"
START, END = dt.date(2026, 9, 1), dt.date(2026, 9, 30)


class September2026Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rates = {}  # {date: {currency: rate}}
        for source in (banque_de_france, uae, argentina, colombia):
            for day, values in source.fetch(START, END).items():
                cls.rates.setdefault(day, {}).update(values)

    def test_every_cell_matches_reference(self):
        # Compared through the exporter, so COP is empty where the reference has it empty.
        exported = export.to_csv(self.rates, START, END, settings.load())
        header, *rows = [line.split(";") for line in exported.split("\r\n")[:-1]]
        expected_header, *expected_rows = [line.split(";") for line in REFERENCE.read_bytes().decode("utf-8").split("\r\n")[:-1]]
        self.assertEqual(header, expected_header)
        self.assertEqual(len(expected_rows), 30)

        differences = []
        for row, expected_row in zip(rows, expected_rows):
            for currency, actual, expected in zip(header[1:], row[1:], expected_row[1:]):
                if actual != expected:
                    differences.append(f"{row[0]} {currency}: reference {expected!r}, source {actual!r}")
        self.assertEqual(differences, [], "\n" + "\n".join(differences))

    def test_aed_close_to_usd_peg(self):
        aed = {day: v["AED"] for day, v in self.rates.items() if "AED" in v}
        usd = {day: v["USD"] for day, v in self.rates.items() if "USD" in v}
        self.assertEqual(uae.check_usd_peg(aed, usd, 1), [])


if __name__ == "__main__":
    unittest.main()
