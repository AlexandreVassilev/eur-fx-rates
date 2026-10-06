"""Builds the CSV for the finance team, in the exact required format:

- columns Date;CHF;HKD;INR;SGD;USD;AED;ARS;COP
- one row per calendar day, newest first, date as dd/mm/yyyy
- decimal comma, no thousands separator, empty cell when nothing was published
- UTF-8 with BOM, Windows line endings (what Excel produces)
The delimiter and decimal mark come from settings.json.
"""

import datetime as dt
from pathlib import Path

from .history import CURRENCIES

BOM = "\ufeff"  # byte order mark: tells Excel the file is UTF-8
LINE_END = "\r\n"


def to_csv(history, start, end, settings):
    """Return the CSV file content (text) for start..end inclusive."""
    if start > end:
        raise ValueError(f"Start date {start} is after end date {end}")
    delimiter, decimal = settings["csv_delimiter"], settings["csv_decimal_mark"]
    lines = [delimiter.join(["Date", *CURRENCIES])]
    day = end
    while day >= start:
        values = history.get(day, {})
        cells = [values.get(cur, "").replace(".", decimal) for cur in CURRENCIES]
        lines.append(delimiter.join([day.strftime("%d/%m/%Y"), *cells]))
        day -= dt.timedelta(days=1)
    return BOM + LINE_END.join(lines) + LINE_END


def write_full_export(history, path, settings):
    """Write the whole history in the final CSV format. The web page cuts the
    chosen date range out of this file, so it never formats numbers itself."""
    if history:
        text = to_csv(history, min(history), max(history), settings)
        Path(path).write_bytes(text.encode("utf-8"))


def currencies_without_data(history, start, end):
    """Currencies with no rate at all between start and end (worth a warning)."""
    days = [d for d in history if start <= d <= end]
    return [cur for cur in CURRENCIES if not any(cur in history[d] for d in days)]
