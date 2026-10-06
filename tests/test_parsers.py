"""Offline tests: each parser reads a saved copy of a real September 2026 response.

Run from the project folder with:  python3 -m unittest -v
"""

import datetime as dt
import unittest
from pathlib import Path

from fxrates import argentina, banque_de_france, colombia, uae
from fxrates.common import FetchError, clean_number

FIXTURES = Path(__file__).parent / "fixtures"
SEPT_1, SEPT_30 = dt.date(2026, 9, 1), dt.date(2026, 9, 30)
SATURDAY = dt.date(2026, 9, 5)


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8-sig")


class CleanNumberTests(unittest.TestCase):
    def test_removes_trailing_zeros_without_rounding(self):
        self.assertEqual(clean_number("1719.51950000"), "1719.5195")
        self.assertEqual(clean_number("3757.91570"), "3757.9157")
        self.assertEqual(clean_number("0,9478"), "0.9478")
        self.assertEqual(clean_number("137,0"), "137")
        self.assertEqual(clean_number("1500"), "1500")  # zeros before the decimal mark are kept

    def test_keeps_zero_and_negative_values_so_they_can_be_flagged(self):
        self.assertEqual(clean_number("0"), "0")
        self.assertEqual(clean_number("-1.5"), "-1.5")

    def test_rejects_text_that_is_not_a_number(self):
        for bad in ["-", "", "N/A", "1.2.3"]:
            with self.assertRaises(FetchError):
                clean_number(bad)


class BanqueDeFranceTests(unittest.TestCase):
    def test_september(self):
        rates = banque_de_france.parse(fixture("banque_de_france_2026-09.csv"), SEPT_1, SEPT_30)
        self.assertEqual(len(rates), 22)  # business days only
        self.assertEqual(
            rates[SEPT_1], {"CHF": "0.9394", "HKD": "9.0877", "INR": "110.0485", "SGD": "1.4759", "USD": "1.159"}
        )
        self.assertNotIn(SATURDAY, rates)
        self.assertEqual(min(rates), SEPT_1)  # 31 August is outside the range
        self.assertEqual(max(rates), SEPT_30)  # 1 October is outside the range

    def test_columns_are_found_by_series_code_not_position(self):
        # Swap the CHF and USD columns in every row: the values must follow their codes.
        lines = []
        for line in fixture("banque_de_france_2026-09.csv").splitlines():
            cells = line.split(";")
            cells[4], cells[29] = cells[29], cells[4]
            lines.append(";".join(cells))
        rates = banque_de_france.parse("\n".join(lines), SEPT_1, SEPT_30)
        self.assertEqual(rates[SEPT_1]["CHF"], "0.9394")
        self.assertEqual(rates[SEPT_1]["USD"], "1.159")

    def test_missing_series_code_is_an_error(self):
        text = fixture("banque_de_france_2026-09.csv").replace("EXR.D.INR.EUR.SP00.A", "SOMETHING.ELSE")
        with self.assertRaises(FetchError):
            banque_de_france.parse(text, SEPT_1, SEPT_30)


class UaeTests(unittest.TestCase):
    def test_business_day(self):
        self.assertEqual(uae.parse(fixture("uae_2026-09-01.html"), SEPT_1), "4.260441")

    def test_weekend_has_no_rate(self):
        self.assertIsNone(uae.parse(fixture("uae_2026-09-05.html"), SATURDAY))

    def test_page_for_another_day_is_an_error(self):
        with self.assertRaises(FetchError):
            uae.parse(fixture("uae_2026-09-01.html"), dt.date(2026, 9, 2))

    def test_usd_peg_check(self):
        usd = {SEPT_1: "1.159"}
        self.assertEqual(uae.check_usd_peg({SEPT_1: "4.260441"}, usd, 1), [])  # 0.09% away: fine
        warnings = uae.check_usd_peg({SEPT_1: "4.35"}, usd, 1)  # about 2.1% away
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0][0], SEPT_1)
        self.assertIn("01/09/2026", warnings[0][1])


class ArgentinaTests(unittest.TestCase):
    def test_september(self):
        rates, total = argentina.parse(fixture("argentina_2026-09.json"))
        self.assertEqual(total, 22)
        self.assertEqual(len(rates), 22)
        self.assertEqual(rates[SEPT_1], {"ARS": "1753.2644"})
        self.assertEqual(rates[SEPT_30], {"ARS": "1719.5195"})  # API sends 1719.51950000
        self.assertNotIn(SATURDAY, rates)


class ColombiaTests(unittest.TestCase):
    def test_september_has_every_calendar_day(self):
        rates = colombia.parse(fixture("colombia_2026-09.json"), SEPT_1, SEPT_30)
        self.assertEqual(len(rates), 30)
        self.assertEqual(rates[SEPT_1], {"COP": "3726.91961"})
        self.assertEqual(rates[SATURDAY], {"COP": "3631.25452"})
        self.assertEqual(rates[dt.date(2026, 9, 28)], {"COP": "3757.9157"})  # API sends 3757.91570

    def test_date_filter(self):
        rates = colombia.parse(fixture("colombia_2026-09.json"), SATURDAY, SATURDAY)
        self.assertEqual(list(rates), [SATURDAY])


if __name__ == "__main__":
    unittest.main()
