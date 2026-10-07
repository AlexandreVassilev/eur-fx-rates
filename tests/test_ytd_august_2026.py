"""Local-only test: export 01/01/2026 to 31/08/2026 from data/rates.csv and
compare it cell by cell with the file sent to the board ("Cours YTD August.csv").

That file is work material and is never committed, so this test is skipped
when it is absent (for example on GitHub). Run from the project folder with:
    python3 -m unittest tests.test_ytd_august_2026 -v

Must be identical: the bytes layout (no BOM, CRLF, final line break), header,
row count, row dates, and which cells are empty, apart from 3 ARS dates.
Values: AED, CHF, SGD and USD must match exactly. The known differences below
come from the reference file or from a different COP method; any other
difference fails the test.
"""

import datetime as dt
import unittest
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fxrates import export, history, settings

PROJECT = Path(__file__).parent.parent
CANDIDATES = [PROJECT / "Cours YTD August.csv", PROJECT / "Cours_YTD_August.csv"]
REFERENCE = next((path for path in CANDIDATES if path.exists()), None)
START, END = dt.date(2026, 1, 1), dt.date(2026, 8, 31)

# ARS days with a value in the reference but none from BCRA (Argentine holidays)
ARS_ONLY_IN_REFERENCE = {"23/03/2026", "24/03/2026", "17/08/2026"}


def number(text):
    """The value of a reference cell, also for broken formats like '1.712.180000'."""
    try:
        return Decimal(text)
    except InvalidOperation:
        whole, _, decimals = text.rpartition(".")
        return Decimal(whole.replace(".", "") + "." + decimals)


def known_difference(currency, day, ours, reference):
    """Why a cell may differ, or None if the difference is unexpected."""
    month = day[3:5]
    if currency == "COP":
        return "COP method (fixed monthly COP per USD x EUR/USD in the reference)"
    if currency == "ARS":
        if day in ARS_ONLY_IN_REFERENCE:
            return "ARS: Argentine holiday, value only in the reference"
        if month == "03" and "23" <= day[:2] <= "27":
            return "ARS: reference shifted two business days (23 to 27 March)"
        if month == "08":
            return "ARS: small August gap"
        if ours and reference and number(reference) == Decimal(ours):
            return "ARS: same value, number written differently in the reference"
    if currency in ("HKD", "INR") and month == "04":
        return f"{currency}: April value mistyped in the reference"
    return None


@unittest.skipUnless(REFERENCE, "reference file 'Cours YTD August.csv' not present (local-only test)")
class YearToDateAugust2026Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ours = export.to_csv(history.load(), START, END, settings.load()).encode("utf-8")
        cls.reference = REFERENCE.read_bytes()
        cls.our_rows = [line.split(";") for line in cls.ours.decode("utf-8").split("\r\n")[:-1]]
        cls.reference_rows = [line.split(";") for line in cls.reference.decode("utf-8").split("\r\n")[:-1]]

    def test_bytes_layout(self):
        for name, data in (("ours", self.ours), ("reference", self.reference)):
            with self.subTest(file=name):
                self.assertFalse(data.startswith(b"\xef\xbb\xbf"), "no BOM")
                self.assertTrue(data.endswith(b"\r\n"), "final line break")
                self.assertEqual(data.count(b"\n"), data.count(b"\r\n"), "only CRLF line endings")
                self.assertEqual(data.count(b"\r"), data.count(b"\r\n"), "only CRLF line endings")

    def test_header_rows_and_dates(self):
        self.assertEqual(self.our_rows[0], self.reference_rows[0])
        self.assertEqual(len(self.our_rows) - 1, 243)
        self.assertEqual(len(self.reference_rows) - 1, 243)
        self.assertEqual([row[0] for row in self.our_rows], [row[0] for row in self.reference_rows])

    def test_empty_cells_in_the_same_places(self):
        header = self.our_rows[0]
        mismatches = []
        for ours, reference in zip(self.our_rows[1:], self.reference_rows[1:]):
            for currency, a, b in zip(header[1:], ours[1:], reference[1:]):
                if (a == "") != (b == "") and not (currency == "ARS" and ours[0] in ARS_ONLY_IN_REFERENCE):
                    mismatches.append(f"{ours[0]} {currency}: ours {a!r}, reference {b!r}")
        self.assertEqual(mismatches, [], "\n" + "\n".join(mismatches))

    def test_only_known_value_differences(self):
        header = self.our_rows[0]
        unexpected = []
        for ours, reference in zip(self.our_rows[1:], self.reference_rows[1:]):
            for currency, a, b in zip(header[1:], ours[1:], reference[1:]):
                if a != b and known_difference(currency, ours[0], a, b) is None:
                    unexpected.append(f"{ours[0]} {currency}: ours {a!r}, reference {b!r}")
        self.assertEqual(unexpected, [], "\n" + "\n".join(unexpected))


if __name__ == "__main__":
    unittest.main()
