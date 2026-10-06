"""Reads settings.json, the one place for settings shared by the Python code and the web page.

csv_delimiter                  character between columns in the exported CSV
csv_decimal_mark               decimal mark in the exported CSV ("," = French style)
history_start                  first date kept in data/rates.csv
refetch_days                   each update re-checks this many recent days, to pick up late publications
move_threshold_percent         flag a day-to-day move larger than this
aed_usd_peg_tolerance_percent  flag AED when it is further than this from USD x 3.6725
stale_after_days               warn when a currency's latest rate is older than this many days
"""

import datetime as dt
import json
from decimal import Decimal
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent.parent / "settings.json"


def load(path=SETTINGS_FILE):
    settings = json.loads(Path(path).read_text(encoding="utf-8"))
    if settings["csv_delimiter"] == settings["csv_decimal_mark"]:
        raise ValueError("csv_delimiter and csv_decimal_mark must be different, or the columns would mix up")
    settings["history_start"] = dt.date.fromisoformat(settings["history_start"])
    for key in ("move_threshold_percent", "aed_usd_peg_tolerance_percent"):
        settings[key] = Decimal(str(settings[key]))
    return settings
