"""Update data/rates.csv, data/status.json and data/export_all.csv from the four central banks.

Run from the project folder with:  python3 update.py

- The first run fills the history from settings.json "history_start" (the UAE
  part needs one request per day, so this takes 15-20 minutes once).
- Later runs only fetch recent days: from each source's latest stored date
  minus "refetch_days" up to today, to pick up late publications.
- Stored rates are never changed. If a source now reports a different value
  for a stored day, the stored value is kept and the difference is reported.
- If a source fails, the others are still saved, the failure is written to
  data/status.json (so the web page can warn), and the script exits with an
  error code (so GitHub Actions marks the run as failed and emails you).
"""

import datetime as dt
import json
import sys
from pathlib import Path

from fxrates import argentina, banque_de_france, checks, colombia, export, history, settings as settings_file, uae
from fxrates.common import FetchError

STATUS_FILE = Path(__file__).parent / "data" / "status.json"
EXPORT_FILE = Path(__file__).parent / "data" / "export_all.csv"  # read by the web page

SOURCES = [  # (name, module, currencies)
    ("Banque de France", banque_de_france, ["CHF", "HKD", "INR", "SGD", "USD"]),
    ("Central Bank of the UAE", uae, ["AED"]),
    ("Banco Central de la República Argentina", argentina, ["ARS"]),
    ("Banco de la República (Colombia)", colombia, ["COP"]),
]


def now_utc():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_window(rates, currencies, settings, today):
    """First day to (re)fetch for a source: its latest stored day minus refetch_days."""
    latest = max((day for day, v in rates.items() if any(c in v for c in currencies)), default=None)
    if latest is None:
        return settings["history_start"]
    return max(settings["history_start"], latest - dt.timedelta(days=settings["refetch_days"]))


def fetch_source(module, rates, currencies, start, today):
    if module is uae:  # one request per day: only ask for days we don't have yet
        days = [start + dt.timedelta(days=n) for n in range((today - start).days + 1)]
        return uae.fetch_days([d for d in days if "AED" not in rates.get(d, {})])
    return module.fetch(start, today)


def main():
    settings = settings_file.load()
    today = dt.datetime.now(dt.timezone.utc).date()
    rates = history.load()
    old_status = json.loads(STATUS_FILE.read_text(encoding="utf-8")) if STATUS_FILE.exists() else {}

    sources_status, conflicts = {}, old_status.get("conflicts", [])
    for name, module, currencies in SOURCES:
        start = fetch_window(rates, currencies, settings, today)
        print(f"{name}: fetching {start} to {today} ...", flush=True)
        previous = old_status.get("sources", {}).get(name, {})
        entry = {"currencies": currencies, "checked_at": now_utc(), "last_success": previous.get("last_success")}
        try:
            new_rates = fetch_source(module, rates, currencies, start, today)
            new_rates = {d: v for d, v in new_rates.items() if d >= settings["history_start"]}
            for conflict in history.merge(rates, new_rates):
                if conflict not in conflicts:
                    conflicts.append(conflict)
                    print(f"  WARNING source changed a stored rate (kept the stored one): {conflict}")
            entry.update(ok=True, error=None, last_success=entry["checked_at"])
            print(f"  ok, {len(new_rates)} days received")
        except (FetchError, OSError, ValueError, KeyError) as error:
            entry.update(ok=False, error=str(error))
            print(f"  FAILED: {error}")
        sources_status[name] = entry

    history.save(rates)
    export.write_full_export(rates, EXPORT_FILE, settings)
    latest = history.latest_dates(rates)
    flags = checks.run_all(rates, latest, settings)
    status = {
        "last_updated": now_utc(),
        "history_start": settings["history_start"].isoformat(),
        "sources": sources_status,
        "latest": {cur: day.isoformat() if day else None for cur, day in latest.items()},
        "conflicts": conflicts,
        "flags": flags,
    }
    STATUS_FILE.write_text(json.dumps(status, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print("Latest rate per currency:", ", ".join(f"{c} {d}" for c, d in status["latest"].items()))
    print(f"{len(flags)} flags, {len(conflicts)} conflicts")
    failed = [name for name, s in sources_status.items() if not s["ok"]]
    if failed:
        print("FAILED sources:", ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
