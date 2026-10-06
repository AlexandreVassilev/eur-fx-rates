"""COP from Banco de la República, Colombia (series 30: "Euro - COP/EUR - Tasa media").

Uses the data service behind https://suameca.banrep.gov.co/descarga-multiple-de-datos/ .
This series has a value for every calendar day: weekends repeat Friday's rate,
and we keep that as-is. (Banco de la República lists Refinitiv as the source.)
"""

import datetime as dt
import json

from .common import FetchError, clean_number, download

URL = "https://suameca.banrep.gov.co/buscador-de-series/rest/buscadorSeriesRestService/consultaDatosSeries"
SERIES_ID = 30   # Euro - COP/EUR - Tasa media
DAILY_DATA = 1   # "Dato diario"

# Dates arrive as timestamps at midnight Bogotá time (UTC-5, no daylight saving).
BOGOTA = dt.timezone(dt.timedelta(hours=-5))


def parse(text, start, end):
    """Return {date: {"COP": rate}} for dates between start and end (inclusive)."""
    series = json.loads(text, parse_float=str, parse_int=str)
    if len(series) != 1 or str(series[0].get("id")) != str(SERIES_ID):
        raise FetchError(f"Banco de la República: expected series {SERIES_ID} only")
    rates = {}
    for timestamp_ms, value in series[0]["data"]:
        moment = dt.datetime.fromtimestamp(int(timestamp_ms) / 1000, BOGOTA)
        if moment.time() != dt.time(0, 0):
            raise FetchError(f"Banco de la República: unexpected timestamp {moment}, date could be shifted")
        if start <= moment.date() <= end and value is not None:
            rates[moment.date()] = {"COP": clean_number(value)}
    return rates


def fetch(start, end):
    body = {
        "series": [{"idSerie": SERIES_ID, "idPeriodicidades": [DAILY_DATA]}],
        "fechaInicio": int(start.strftime("%Y%m%d")),
        "fechaFin": int(end.strftime("%Y%m%d")),
    }
    text = download(URL, json.dumps(body).encode(), {"Content-type": "application/json"})
    return parse(text, start, end)
