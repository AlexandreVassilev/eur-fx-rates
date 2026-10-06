"""Offline tests for the history file, the quality checks and the CSV export.

Run from the project folder with:  python3 -m unittest -v
"""

import datetime as dt
import tempfile
import unittest
from pathlib import Path

from fxrates import argentina, banque_de_france, checks, colombia, export, history, settings as settings_file, uae
from fxrates.history import CURRENCIES

TESTS = Path(__file__).parent
FIXTURES = TESTS / "fixtures"
SEPT_1, SEPT_30 = dt.date(2026, 9, 1), dt.date(2026, 9, 30)
SETTINGS = settings_file.load()


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8-sig")


def september_from_fixtures():
    """Build the September 2026 history from the saved source responses (no internet)."""
    rates = {}
    history.merge(rates, banque_de_france.parse(fixture("banque_de_france_2026-09.csv"), SEPT_1, SEPT_30))
    history.merge(rates, argentina.parse(fixture("argentina_2026-09.json"))[0])
    history.merge(rates, colombia.parse(fixture("colombia_2026-09.json"), SEPT_1, SEPT_30))
    # The UAE fixture only has 1 September; the other AED values come from the reference file.
    history.merge(rates, {SEPT_1: {"AED": uae.parse(fixture("uae_2026-09-01.html"), SEPT_1)}})
    for line in (TESTS / "september_2026_reference.csv").read_text(encoding="utf-8-sig").splitlines()[1:]:
        cells = line.split(";")
        if cells[6]:
            day = dt.datetime.strptime(cells[0], "%d/%m/%Y").date()
            history.merge(rates, {day: {"AED": cells[6].replace(",", ".")}})
    return rates


class ExportTests(unittest.TestCase):
    def test_september_is_byte_for_byte_identical_to_reference(self):
        csv_text = export.to_csv(september_from_fixtures(), SEPT_1, SEPT_30, SETTINGS)
        self.assertEqual(csv_text.encode("utf-8"), (TESTS / "september_2026_reference.csv").read_bytes())

    def test_format_details(self):
        rates = {dt.date(2026, 9, 4): {"USD": "1.1622", "COP": "3649.00377"}}
        csv_text = export.to_csv(rates, dt.date(2026, 9, 4), dt.date(2026, 9, 5), SETTINGS)
        self.assertTrue(csv_text.startswith("\ufeffDate;CHF;HKD;INR;SGD;USD;AED;ARS;COP\r\n"))
        lines = csv_text[1:].split("\r\n")
        self.assertEqual(lines[1], "05/09/2026;;;;;;;;")  # newest first; empty, never 0 or N/A
        self.assertEqual(lines[2], "04/09/2026;;;;;1,1622;;;3649,00377")
        self.assertEqual(lines[3], "")  # file ends with a line break

    def test_one_row_per_calendar_day(self):
        csv_text = export.to_csv({}, dt.date(2024, 2, 1), dt.date(2024, 3, 1), SETTINGS)
        self.assertEqual(len(csv_text.strip().split("\r\n")), 1 + 30)  # header + Feb (leap year) + 1 March

    def test_start_after_end_is_an_error(self):
        with self.assertRaises(ValueError):
            export.to_csv({}, SEPT_30, SEPT_1, SETTINGS)

    def test_delimiter_comes_from_settings(self):
        settings = {**SETTINGS, "csv_delimiter": ",", "csv_decimal_mark": "."}
        csv_text = export.to_csv({SEPT_1: {"CHF": "0.9394"}}, SEPT_1, SEPT_1, settings)
        self.assertIn("Date,CHF,HKD", csv_text)
        self.assertIn("01/09/2026,0.9394,,", csv_text)

    def test_same_delimiter_and_decimal_mark_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(SETTINGS_FILE_TEXT.replace('"csv_decimal_mark": ","', '"csv_decimal_mark": ";"'))
            with self.assertRaises(ValueError):
                settings_file.load(path)

    def test_currencies_without_data(self):
        rates = september_from_fixtures()
        self.assertEqual(export.currencies_without_data(rates, SEPT_1, SEPT_30), [])
        self.assertEqual(export.currencies_without_data(rates, dt.date(2026, 9, 5), dt.date(2026, 9, 6)),
                         [c for c in CURRENCIES if c != "COP"])


SETTINGS_FILE_TEXT = settings_file.SETTINGS_FILE.read_text(encoding="utf-8")


class HistoryTests(unittest.TestCase):
    def test_save_and_load_keep_every_value_and_every_day(self):
        rates = september_from_fixtures()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rates.csv"
            history.save(rates, path)
            self.assertEqual(history.load(path), {d: v for d, v in rates.items() if v})
            self.assertEqual(len(path.read_text().splitlines()), 1 + 30)  # weekends are rows too

    def test_merge_never_changes_a_stored_rate(self):
        rates = {SEPT_1: {"USD": "1.159"}}
        conflicts = history.merge(rates, {SEPT_1: {"USD": "1.2", "CHF": "0.9394"}})
        self.assertEqual(rates[SEPT_1], {"USD": "1.159", "CHF": "0.9394"})  # USD kept, CHF added
        self.assertEqual(conflicts, [{"date": "2026-09-01", "currency": "USD", "stored": "1.159", "source_now": "1.2"}])

    def test_latest_dates(self):
        latest = history.latest_dates(september_from_fixtures())
        self.assertEqual(latest["USD"], SEPT_30)
        self.assertEqual(latest["COP"], SEPT_30)


class CheckTests(unittest.TestCase):
    def kinds(self, rates):
        return [(f["date"], f["currency"], f["kind"]) for f in checks.run_all(rates, history.latest_dates(rates), SETTINGS)]

    def test_september_has_no_flags(self):
        self.assertEqual(self.kinds(september_from_fixtures()), [])

    def test_big_move_above_threshold(self):
        rates = {SEPT_1: {"ARS": "100"}, dt.date(2026, 9, 2): {"ARS": "103.5"}, dt.date(2026, 9, 3): {"ARS": "105"}}
        # +3.5% is flagged; +1.4% is not
        self.assertEqual(self.kinds(rates), [("2026-09-02", "ARS", "big_move")])

    def test_big_move_compares_with_previous_available_rate(self):
        # Friday 4 Sept -> Monday 7 Sept, the weekend in between has no rate
        rates = {dt.date(2026, 9, 4): {"ARS": "100"}, dt.date(2026, 9, 7): {"ARS": "95"}}
        self.assertEqual(self.kinds(rates), [("2026-09-07", "ARS", "big_move")])

    def test_zero_and_negative(self):
        rates = {SEPT_1: {"CHF": "0"}, dt.date(2026, 9, 2): {"CHF": "-1"}}
        self.assertEqual(self.kinds(rates), [("2026-09-01", "CHF", "zero_or_negative"),
                                             ("2026-09-02", "CHF", "zero_or_negative")])

    def test_missing_weekday_but_not_weekend(self):
        # Fri 4 Sept and Tue 8 Sept have CHF; Mon 7 Sept is missing; Sat/Sun are normal
        rates = {dt.date(2026, 9, 4): {"CHF": "0.94"}, dt.date(2026, 9, 8): {"CHF": "0.94"}}
        self.assertEqual(self.kinds(rates), [("2026-09-07", "CHF", "missing_weekday")])

    def test_cop_missing_any_day(self):
        rates = {dt.date(2026, 9, 4): {"COP": "3649"}, dt.date(2026, 9, 6): {"COP": "3631"}}
        self.assertEqual(self.kinds(rates), [("2026-09-05", "COP", "missing_day")])

    def test_aed_far_from_usd_peg(self):
        rates = {SEPT_1: {"USD": "1.159", "AED": "4.35"}}
        self.assertEqual(self.kinds(rates), [("2026-09-01", "AED", "aed_usd_peg")])


if __name__ == "__main__":
    unittest.main()
