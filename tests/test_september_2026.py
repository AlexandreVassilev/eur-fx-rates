"""Live test: fetch September 2026 from all four central banks and compare
every cell with the hand-made reference file. Needs an internet connection
and takes about a minute (the UAE source needs one request per day).

Run from the project folder with:  python3 -m unittest tests.test_september_2026 -v
"""

import csv
import datetime as dt
import unittest
from pathlib import Path

from fxrates import argentina, banque_de_france, colombia, uae

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
        with open(REFERENCE, encoding="utf-8-sig", newline="") as file:
            header, *rows = list(csv.reader(file, delimiter=";"))
        self.assertEqual(len(rows), 30)

        differences = []
        for row in rows:
            day = dt.datetime.strptime(row[0], "%d/%m/%Y").date()
            for currency, expected in zip(header[1:], row[1:]):
                actual = self.rates.get(day, {}).get(currency, "").replace(".", ",")
                if actual != expected:
                    differences.append(f"{row[0]} {currency}: reference {expected!r}, source {actual!r}")
        self.assertEqual(differences, [], "\n" + "\n".join(differences))

    def test_aed_close_to_usd_peg(self):
        aed = {day: v["AED"] for day, v in self.rates.items() if "AED" in v}
        usd = {day: v["USD"] for day, v in self.rates.items() if "USD" in v}
        self.assertEqual(uae.check_usd_peg(aed, usd, 1), [])


if __name__ == "__main__":
    unittest.main()
