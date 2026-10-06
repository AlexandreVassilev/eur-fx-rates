"""Small helpers shared by all the fetchers."""

import ssl
import time
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Some sites refuse requests that don't look like they come from a browser.
USER_AGENT = "Mozilla/5.0 (compatible; eur-fx-rates)"
TIMEOUT_SECONDS = 60
ATTEMPTS = 3
RETRY_WAIT_SECONDS = 5

# Normal certificate checking, plus intermediate certificates that some
# servers forget to send (Banco de la República omits "GeoTrust EV RSA CA G2").
# Checking is never switched off.
SSL_CONTEXT = ssl.create_default_context()
for certificate in sorted((Path(__file__).parent / "certificates").glob("*.pem")):
    SSL_CONTEXT.load_verify_locations(certificate)


class FetchError(Exception):
    """Raised when a source can't be reached or returns something unexpected."""


def download(url, body=None, headers=None):
    """Download a URL and return its text. Sends a POST if `body` is given.

    Tries up to ATTEMPTS times, waiting a little longer each time, because
    central-bank servers sometimes fail for a moment.
    """
    request = urllib.request.Request(url, data=body, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=SSL_CONTEXT) as response:
                return response.read().decode("utf-8-sig")  # "-sig" drops a BOM if there is one
        except OSError as error:  # covers network errors, timeouts and HTTP errors
            if attempt == ATTEMPTS:
                raise FetchError(f"Could not download {url} after {ATTEMPTS} attempts: {error}") from error
            time.sleep(RETRY_WAIT_SECONDS * attempt)


def clean_number(text):
    """Turn a rate as written by a source into plain text like '1719.5195'.

    Accepts '.' or ',' as the decimal mark and removes trailing zeros
    ('1719.51950000' -> '1719.5195'). Never rounds. Raises FetchError if the
    text is not a number at all. Zero or negative values are kept as-is:
    they are flagged later, never changed.
    """
    value = text.strip().replace(",", ".")
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise FetchError(f"Not a number: {text!r}") from None
    if not number.is_finite():
        raise FetchError(f"Not a number: {text!r}")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value
