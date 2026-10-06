# Taux de change EUR

A small page showing daily exchange rates against the euro (1 EUR = X units of
the currency) for CHF, HKD, INR, SGD, USD, AED, ARS and COP, with a CSV
download for any date range.

*(The sections for the page's users and for maintenance will be added in Phase 5.)*

## Sources: what the page links to, and what we really fetch

The panel "Source utilisée" on the page links to each bank's **public page**,
so a reader can check where the numbers come from. The program does **not**
read those pages. It reads the technical addresses below, which return the
same data in a form a program can use. All four need no login and no key.

| Source (as named on the page) | Currencies | Page linked on the page | Address the program really fetches | Same address? |
|---|---|---|---|---|
| Banque de France (taux de référence de la BCE) | CHF, HKD, INR, SGD, USD | https://www.banque-france.fr/fr/publications-et-statistiques/statistiques | `https://webstat.banque-france.fr/export/csv-columns/fr/selection/5385698` | **No** (see 1) |
| Banque centrale des Émirats arabes unis | AED | https://centralbank.ae/en/forex-eibor/exchange-rates/ | `https://centralbank.ae/umbraco/Surface/Exchange/GetExchangeRateAllCurrencyDate?dateTime=YYYY-MM-DD` (one request per day) | **No** (see 2) |
| Banque centrale d'Argentine (BCRA) | ARS | https://www.bcra.gob.ar/evolucion-moneda/ | `https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/EUR?fechadesde=YYYY-MM-DD&fechahasta=YYYY-MM-DD` | **No** (see 3) |
| Banque de la République (Colombie) | COP | https://suameca.banrep.gov.co/descarga-multiple-de-datos/ | `https://suameca.banrep.gov.co/buscador-de-series/rest/buscadorSeriesRestService/consultaDatosSeries` (see 4) | **No** (see 4) |

None of the four is the same address as the linked page. In each case the
program reads the data behind the page, from the same bank. The values were
checked against the hand-made September 2026 file
(`tests/september_2026_reference.csv`): all 240 cells match.

1. **Banque de France.** The link opens the Banque de France statistics home
   page, a general page, not this exact series. The program downloads a saved
   selection from Webstat, the bank's statistics portal (a different web
   address, `webstat.banque-france.fr`). It contains the ECB reference rates
   (the file's own "Source" line says "BCE"). The columns are found by their
   series codes: `EXR.D.CHF.EUR.SP00.A`, `EXR.D.HKD.EUR.SP00.A`,
   `EXR.D.INR.EUR.SP00.A`, `EXR.D.SGD.EUR.SP00.A`, `EXR.D.USD.EUR.SP00.A`.
2. **UAE.** Same website as the link, but a different address. The linked page
   is protected by a robot check (Cloudflare) that programs cannot pass. The
   program uses the request the page itself makes to show one day's table of
   rates, and reads the "Euro" line. This is **not** the request behind the
   page's Excel download button: that button sits behind the robot check and
   could not be inspected. The values are the same as in your Excel downloads.
3. **Argentina.** The link opens the page where the CSV is downloaded by hand.
   The program uses the bank's official public API (a different web address,
   `api.bcra.gob.ar`), field `tipoCotizacion` for EUR.
4. **Colombia.** Same website as the link, but a different address: the data
   service that the page itself uses. The program sends it this request (a
   "POST"), asking for series 30, "Euro - COP/EUR - Tasa media", daily data:
   `{"series":[{"idSerie":30,"idPeriodicidades":[1]}],"fechaInicio":YYYYMMDD,"fechaFin":YYYYMMDD}`.
   The bank lists this series as sourced from **Refinitiv** (a commercial data
   provider), so it is a rate republished by the bank, not one the bank sets.
   This server does not send its full chain of security certificates, so the
   project includes the missing public "intermediate" certificate
   (`fxrates/certificates/GeoTrustEVRSACAG2.pem`, issued by DigiCert, valid
   until 2030). Security checks stay fully on.
