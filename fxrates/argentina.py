"""ARS from Banco Central de la República Argentina (official public API)."""

import datetime as dt
import json

from .common import FetchError, clean_number, download

URL = "https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/EUR?fechadesde={start}&fechahasta={end}&limit={limit}&offset={offset}"
PAGE_SIZE = 1000  # the API returns at most 1000 days per request


def parse(text):
    """Return ({date: {"ARS": rate}}, total row count) from one API response."""
    # parse_float=str keeps each number exactly as the API wrote it (no float rounding).
    data = json.loads(text, parse_float=str, parse_int=str)
    if str(data.get("status")) != "200":
        raise FetchError(f"BCRA API returned status {data.get('status')}: {data.get('errorMessages')}")
    rates = {}
    for entry in data["results"]:
        day = dt.date.fromisoformat(entry["fecha"])
        for quote in entry["detalle"]:
            if quote["codigoMoneda"] == "EUR":
                rates[day] = {"ARS": clean_number(quote["tipoCotizacion"])}
    return rates, int(data["metadata"]["resultset"]["count"])


def fetch(start, end):
    rates, offset = {}, 0
    while True:
        page, total = parse(download(URL.format(start=start, end=end, limit=PAGE_SIZE, offset=offset)))
        rates.update(page)
        offset += PAGE_SIZE
        if offset >= total:
            return rates
