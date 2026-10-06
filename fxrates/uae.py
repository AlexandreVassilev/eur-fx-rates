"""AED from the Central Bank of the UAE.

The main exchange-rates page is behind a Cloudflare robot check, but the
request that loads one day's table of rates is not. That table is a piece of
web page (HTML), so we read the line "Euro 4.260441" from it. One request per
day, with a short pause between requests to be polite to their server.
"""

import datetime as dt
import html
import re
import time
from decimal import Decimal

from .common import FetchError, clean_number, download

URL = "https://centralbank.ae/umbraco/Surface/Exchange/GetExchangeRateAllCurrencyDate?dateTime={day}"
PAUSE_SECONDS = 1.0

# The dirham is pegged to the US dollar: 1 USD = 3.6725 AED.
USD_PEG = Decimal("3.6725")


def parse(page, day):
    """Return the EUR rate for `day`, or None if the bank published nothing that day."""
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))
    euro = re.findall(r"\bEuro ([0-9][0-9.,]*)", text)
    if not euro:
        return None  # weekend, holiday or not published yet
    if len(euro) > 1:
        raise FetchError(f"UAE: found {len(euro)} Euro rates for {day}, expected one")

    # Safety check: the page must be for the day we asked about.
    updated = re.search(r"Last updated: \w+ (\d{1,2} \w+ \d{4})", text)
    if not updated:
        raise FetchError(f"UAE: no 'Last updated' date on the page for {day}")
    page_day = dt.datetime.strptime(updated.group(1), "%d %B %Y").date()
    if page_day != day:
        raise FetchError(f"UAE: asked for {day} but the page is for {page_day}")
    return clean_number(euro[0])


def fetch(start, end):
    """Return {date: {"AED": rate}} for dates between start and end (inclusive)."""
    return fetch_days([start + dt.timedelta(days=n) for n in range((end - start).days + 1)])


def fetch_days(days):
    """Return {date: {"AED": rate}} for the given days (one request each)."""
    rates = {}
    for number, day in enumerate(days):
        if number:
            time.sleep(PAUSE_SECONDS)
        rate = parse(download(URL.format(day=day.isoformat())), day)
        if rate is not None:
            rates[day] = {"AED": rate}
    return rates


def check_usd_peg(aed_rates, usd_rates, tolerance_percent):
    """Return (date, warning message) for each day where AED is further than
    `tolerance_percent` (1 = 1%) away from USD x 3.6725.

    Both rate arguments are {date: rate text}. Only a warning: rates are never changed.
    """
    warnings = []
    for day in sorted(aed_rates.keys() & usd_rates.keys()):
        expected = Decimal(usd_rates[day]) * USD_PEG
        if expected <= 0:
            continue  # zero or negative rates get their own warning elsewhere
        gap = abs(Decimal(aed_rates[day]) / expected - 1)
        if gap * 100 > Decimal(tolerance_percent):
            message = (f"AED : {aed_rates[day]} le {day:%d/%m/%Y}, écart de {gap * 100:.2f} % avec "
                       f"USD {usd_rates[day]} × {USD_PEG} = {expected:.6f}").replace(".", ",")
            warnings.append((day, message))
    return warnings
