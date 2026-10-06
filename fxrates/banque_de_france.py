"""CHF, HKD, INR, SGD, USD from Banque de France (ECB reference rates).

One fixed URL returns the whole history since 1999 as a semicolon CSV.
Columns are found by their official series code, never by position, so a
new or moved column can't silently swap currencies.
"""

import csv
import datetime as dt

from .common import FetchError, clean_number, download

URL = "https://webstat.banque-france.fr/export/csv-columns/fr/selection/5385698"

# Currency -> series code in the "Code série" header row.
SERIES_CODES = {
    "CHF": "EXR.D.CHF.EUR.SP00.A",
    "HKD": "EXR.D.HKD.EUR.SP00.A",
    "INR": "EXR.D.INR.EUR.SP00.A",
    "SGD": "EXR.D.SGD.EUR.SP00.A",
    "USD": "EXR.D.USD.EUR.SP00.A",
}
NO_RATE = {"-", ""}  # what the file shows on weekends and holidays


def parse(text, start, end):
    """Return {date: {currency: rate}} for dates between start and end (inclusive)."""
    rows = list(csv.reader(text.splitlines(), delimiter=";"))
    code_row = next((row for row in rows if row and row[0].startswith("Code série")), None)
    if code_row is None:
        raise FetchError("Banque de France: header row 'Code série' not found")

    columns = {}
    for currency, code in SERIES_CODES.items():
        if code_row.count(code) != 1:
            raise FetchError(f"Banque de France: series {code} found {code_row.count(code)} times, expected once")
        columns[currency] = code_row.index(code)

    rates = {}
    for row in rows:
        try:
            day = dt.date.fromisoformat(row[0])
        except (IndexError, ValueError):
            continue  # header or metadata row, not a data row
        if not start <= day <= end:
            continue
        values = {cur: clean_number(row[col]) for cur, col in columns.items() if row[col].strip() not in NO_RATE}
        if values:
            rates[day] = values
    return rates


def fetch(start, end):
    return parse(download(URL), start, end)
