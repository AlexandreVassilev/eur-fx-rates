"""Builds the CSV for the finance team, in the exact required format
(the format of the file sent to the board, "Cours YTD August.csv"):

- columns Date;AED;ARS;CHF;COP;HKD;INR;SGD;USD
- one row per calendar day, oldest first, date as dd/mm/yyyy
- decimal point, no thousands separator, empty cell when nothing was published
- no BOM, Windows line endings (CRLF), a line break after the last row
- COP is left empty on days when the five Banque de France currencies are all
  empty (weekends and ECB holidays). Only in the export: data/rates.csv keeps
  every COP value.
The delimiter and decimal mark come from settings.json.
"""

import datetime as dt
from pathlib import Path

COLUMNS = ["AED", "ARS", "CHF", "COP", "HKD", "INR", "SGD", "USD"]
BANQUE_DE_FRANCE = ["CHF", "HKD", "INR", "SGD", "USD"]
LINE_END = "\r\n"


def export_values(values):
    """The rates of one day as exported: COP dropped when no ECB rate exists that day."""
    if not any(cur in values for cur in BANQUE_DE_FRANCE):
        return {cur: rate for cur, rate in values.items() if cur != "COP"}
    return values


def to_csv(history, start, end, settings):
    """Return the CSV file content (text) for start..end inclusive."""
    if start > end:
        raise ValueError(f"Start date {start} is after end date {end}")
    delimiter, decimal = settings["csv_delimiter"], settings["csv_decimal_mark"]
    lines = [delimiter.join(["Date", *COLUMNS])]
    day = start
    while day <= end:
        values = export_values(history.get(day, {}))
        cells = [values.get(cur, "").replace(".", decimal) for cur in COLUMNS]
        lines.append(delimiter.join([day.strftime("%d/%m/%Y"), *cells]))
        day += dt.timedelta(days=1)
    return LINE_END.join(lines) + LINE_END


def write_full_export(history, path, settings):
    """Write the whole history in the final CSV format. The web page cuts the
    chosen date range out of this file, so it never formats numbers itself."""
    if history:
        text = to_csv(history, min(history), max(history), settings)
        Path(path).write_bytes(text.encode("utf-8"))


def currencies_without_data(history, start, end):
    """Currencies with no rate at all between start and end (worth a warning)."""
    days = [d for d in history if start <= d <= end]
    return [cur for cur in COLUMNS if not any(cur in history[d] for d in days)]
