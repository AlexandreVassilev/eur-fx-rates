"""Quality checks on the history. They only flag: rates are never changed.

Each flag is a dict: {"date": "2026-09-14", "currency": "AED", "kind": ..., "message": ...}
Messages are in French because they are shown on the (French) web page.
Kinds:
  missing_weekday  no rate on a Monday-Friday (often a public holiday; worth a look)
  missing_day      COP has no rate on a day (COP should have every calendar day)
  zero_or_negative a rate of 0 or below
  big_move         change from the previous available rate above the threshold
  aed_usd_peg      AED too far from USD x 3.6725
"""

import datetime as dt
from decimal import Decimal

from . import uae
from .history import CURRENCIES

EVERY_DAY = {"COP"}  # currencies published on every calendar day
WEEKDAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def fr(number):
    """French number text: decimal comma (1217.3854 -> '1217,3854')."""
    return str(number).replace(".", ",")


def flag(day, currency, kind, message):
    return {"date": day.isoformat(), "currency": currency, "kind": kind, "message": message}


def run_all(history, latest, settings):
    """Return all flags for the whole history. `latest` is {currency: latest date}."""
    flags = []
    if not history:
        return flags
    first = min(history)
    for currency in CURRENCIES:
        previous = None  # (day, value) of the previous available rate
        day = first
        while latest[currency] and day <= latest[currency]:
            rate = history.get(day, {}).get(currency)
            if rate is None:
                if currency in EVERY_DAY:
                    flags.append(flag(day, currency, "missing_day", f"{currency} : aucun taux le {day:%d/%m/%Y}"))
                elif day.weekday() < 5:
                    flags.append(flag(day, currency, "missing_weekday",
                                      f"{currency} : aucun taux le {WEEKDAYS_FR[day.weekday()]} "
                                      f"{day:%d/%m/%Y} (jour férié ?)"))
            else:
                value = Decimal(rate)
                if value <= 0:
                    flags.append(flag(day, currency, "zero_or_negative",
                                      f"{currency} : taux nul ou négatif ({fr(rate)}) le {day:%d/%m/%Y}"))
                elif previous and previous[1] > 0:
                    move = (value / previous[1] - 1) * 100
                    if abs(move) > settings["move_threshold_percent"]:
                        flags.append(flag(day, currency, "big_move",
                                          f"{currency} : variation de {fr(f'{move:+.2f}')} % le {day:%d/%m/%Y} "
                                          f"({fr(previous[1])} le {previous[0]:%d/%m/%Y} → {fr(rate)})"))
                previous = (day, value)
            day += dt.timedelta(days=1)

    aed = {day: v["AED"] for day, v in history.items() if "AED" in v}
    usd = {day: v["USD"] for day, v in history.items() if "USD" in v}
    for day, message in uae.check_usd_peg(aed, usd, settings["aed_usd_peg_tolerance_percent"]):
        flags.append(flag(day, "AED", "aed_usd_peg", message))
    return sorted(flags, key=lambda f: (f["date"], CURRENCIES.index(f["currency"]), f["kind"]))
