"""Export a date range from data/rates.csv in the finance team's CSV format.

Run from the project folder, for example:
    python3 export_csv.py 2026-09-01 2026-09-30
    python3 export_csv.py 2026-09-01 2026-09-30 my_file.csv
Without a file name it writes fx_rates_<start>_<end>.csv in the current folder.
"""

import datetime as dt
import json
import sys
from pathlib import Path

from fxrates import export, history, settings as settings_file
from update import STATUS_FILE


def main():
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    start, end = dt.date.fromisoformat(sys.argv[1]), dt.date.fromisoformat(sys.argv[2])
    output = Path(sys.argv[3] if len(sys.argv) == 4 else f"fx_rates_{start}_{end}.csv")

    rates = history.load()
    output.write_bytes(export.to_csv(rates, start, end, settings_file.load()).encode("utf-8"))
    print(f"Wrote {output} ({(end - start).days + 1} days)")

    # Warnings for this range: never change the data, just tell the reader.
    for currency in export.currencies_without_data(rates, start, end):
        print(f"WARNING: no {currency} rate at all between {start} and {end}")
    status = json.loads(STATUS_FILE.read_text(encoding="utf-8")) if STATUS_FILE.exists() else {"flags": []}
    for flag in status["flags"]:
        if start.isoformat() <= flag["date"] <= end.isoformat():
            print("FLAG:", flag["message"])


if __name__ == "__main__":
    main()
