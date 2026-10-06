"""The daily history file, data/rates.csv.

One row per calendar day, oldest first, raw values exactly as the sources gave
them (dot decimal, trailing zeros removed), empty when nothing was published:

    date,CHF,HKD,INR,SGD,USD,AED,ARS,COP
    2026-09-01,0.9394,9.0877,110.0485,1.4759,1.159,4.260441,1753.2644,3726.91961
    2026-09-05,,,,,,,,3631.25452
"""

import csv
import datetime as dt
import os
from pathlib import Path

CURRENCIES = ["CHF", "HKD", "INR", "SGD", "USD", "AED", "ARS", "COP"]
RATES_FILE = Path(__file__).parent.parent / "data" / "rates.csv"


def load(path=RATES_FILE):
    """Return {date: {currency: rate}}. Missing file -> empty history."""
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ["date", *CURRENCIES]:
            raise ValueError(f"{path} has unexpected columns: {reader.fieldnames}")
        return {
            dt.date.fromisoformat(row["date"]): {cur: row[cur] for cur in CURRENCIES if row[cur]}
            for row in reader
        }


def save(history, path=RATES_FILE):
    """Write the history, one row per calendar day from the first to the last date."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with open(temporary, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["date", *CURRENCIES])
        if history:
            day, last = min(history), max(history)
            while day <= last:
                values = history.get(day, {})
                writer.writerow([day.isoformat(), *(values.get(cur, "") for cur in CURRENCIES)])
                day += dt.timedelta(days=1)
    os.replace(temporary, path)  # swap in the new file only once it is complete


def merge(history, new_rates):
    """Add newly fetched rates to the history. Never changes a stored rate.

    Returns a list of conflicts: cases where a source now reports a different
    value for a day we already stored. The stored value is kept, and the
    conflict is reported so a person can look at it.
    """
    conflicts = []
    for day, values in new_rates.items():
        stored = history.setdefault(day, {})
        for currency, rate in values.items():
            if currency not in stored:
                stored[currency] = rate
            elif stored[currency] != rate:
                conflicts.append({"date": day.isoformat(), "currency": currency, "stored": stored[currency], "source_now": rate})
    return conflicts


def latest_dates(history):
    """Return {currency: latest date with a rate} (None if never)."""
    return {cur: max((day for day, v in history.items() if cur in v), default=None) for cur in CURRENCIES}
