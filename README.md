# Taux de change EUR

A small web page with daily exchange rates against the euro (1 EUR = X units
of the currency) for AED, ARS, CHF, COP, HKD, INR, SGD and USD, and a CSV
download for any date range.

Page: https://alexandrevassilev.github.io/eur-fx-rates/

The rates are updated automatically twice a day, at 21:17 and 06:47 Paris
time, from four central banks (see "Sources" at the end).

---

# For the reader of the page (how to use the page and the CSV)

## Getting the rates for a period

1. Open the page.
2. Choose the dates:
   - click **"Dernier mois complet"** to get the last full month (for example,
     on 7 October you get 1 to 30 September), or
   - click the yellow **"Début"** and **"Fin"** boxes and pick the first and
     the last day.
3. The table appears under the buttons. It shows exactly what will be in the file.
4. Click **"Télécharger en CSV"**. The file is called
   `taux_de_change_<start>_<end>.csv`, for example
   `taux_de_change_2026-09-01_2026-09-30.csv`.

The line "Dernière mise à jour" at the top says when the rates were last updated.

## What the CSV file looks like

It has the same format as the file sent to the board:

```
Date;AED;ARS;CHF;COP;HKD;INR;SGD;USD
01/09/2026;4.260441;1753.2644;0.9394;3726.91961;9.0877;110.0485;1.4759;1.159
...
05/09/2026;;;;;;;;
```

- One row per calendar day, oldest date first. Dates are written dd/mm/yyyy.
- Columns are separated by a semicolon (`;`).
- Numbers use a decimal **point** (`1.159`), with no thousands separator.
  They are exactly as the bank published them: never rounded, only
  zeros at the end are removed (`1.1590` becomes `1.159`).
- An **empty cell** means the bank published no rate that day (weekends and
  public holidays). It is never filled with 0, "N/A" or the previous day's rate.
- **COP** is left empty on days when the five European Central Bank currencies
  (CHF, HKD, INR, SGD, USD) are all empty, that is on weekends and ECB holidays.
  The Colombian bank does publish a rate on those days; it is kept in the
  project's history, just not put in the file.
- Technical details: plain text (UTF-8, no "BOM"), Windows line endings,
  a line break after the last row.

## Messages on the page

- **"Attention :"** at the top (in a red box) means something needs a
  look: a bank could not be reached at the last update, or a currency's latest
  rate is more than 4 days old. The rates already shown are still correct;
  only the most recent days may be missing.
- **"Alertes pour cette période"** under the table lists unusual values in the
  chosen period: a change of more than 3% from one rate to the next, an AED
  rate more than 1% away from the US dollar peg (USD x 3.6725), or a rate of
  zero or below. These are warnings only: **the program never changes a rate.**
- A **"Conflit"** message means a bank changed a rate after it was first
  saved. The first value is kept, and the person who maintains the page
  decides which one is right.

---

# For the maintainer (how to make changes)

## What is where

| File or folder | What it does |
|---|---|
| `index.html`, `style.css`, `app.js` | The web page (in French). It only reads files; it never formats numbers. |
| `update.py` | Fetches new rates from the four banks. Run by the robot twice a day. |
| `export_csv.py` | Makes a CSV for a date range from the command line. |
| `fxrates/` | The Python code: one file per bank, the history, the checks, and `export.py`, the **only** place that formats the CSV. |
| `settings.json` | Settings shared by the Python code and the page (see below). |
| `data/rates.csv` | The full history: every rate, exactly as received. Never edited by the program once saved. |
| `data/export_all.csv` | The whole history in the final CSV format. The page cuts the chosen dates out of it. |
| `data/status.json` | Last update time, failed sources, conflicts and alerts. Read by the page. |
| `tests/` | Automatic checks, and saved bank answers to test with no internet. |
| `.github/workflows/` | The robot (`update.yml`) and the connection test (`connection-test.yml`). |

## Making a change, step by step

1. **Always start with `git pull`.** The robot saves new rates to GitHub twice
   a day, so your copy is out of date until you pull.
2. Make the change.
3. Run the checks from the project folder:
   ```
   python3 -m unittest -v
   ```
   This runs everything: the offline checks, the page checks (Mac only), the
   comparison with the board file (only if `Cours YTD August.csv` is in the
   folder) and a live download of September 2026 from the four banks (needs
   internet, about a minute). Everything should say `ok` or `skipped`.
4. Look at the page on your Mac:
   ```
   python3 -m http.server 8000
   ```
   then open http://localhost:8000 . Press Ctrl+C in the terminal to stop it.
5. Save and publish:
   ```
   git add -A
   git commit -m "What I changed"
   git push
   ```
   If `git push` is refused because the robot pushed in the meantime, run
   `git pull --rebase` and then `git push` again.
6. The live page updates one or two minutes after the push.

Private files (`brief.md`, `phase3.md`, `sketch.jpg`, `format_update.md`,
`Cours YTD August.csv`) are listed in `.git/info/exclude`, so git ignores them
and they are never published.

## Settings (`settings.json`)

| Setting | Meaning |
|---|---|
| `csv_delimiter` | Character between columns in the CSV (`;`). |
| `csv_decimal_mark` | Decimal mark in the CSV (`.`). Must differ from the delimiter, or the program refuses to start. |
| `history_start` | First date kept in the history. |
| `refetch_days` | Each update re-checks this many recent days, to catch rates published late. |
| `move_threshold_percent` | Alert when a rate moves more than this (%) from the previous one. |
| `aed_usd_peg_tolerance_percent` | Alert when AED is further than this (%) from USD x 3.6725. |
| `stale_after_days` | Warn on the page when a currency's latest rate is older than this. |

## Making a CSV by hand

```
python3 export_csv.py 2026-09-01 2026-09-30
```
writes `fx_rates_2026-09-01_2026-09-30.csv` in the same format as the page,
and prints any alerts for that period.

## If a source breaks

You will notice it in one of three ways: GitHub emails you that the run
"Mise à jour des taux" failed, the page shows "Attention : La dernière mise à
jour de la source ... a échoué", or a currency's latest rate gets old.

The other sources are still saved when one fails. And once the source works
again, the next update **catches up by itself**: it fetches everything from
the last saved day onwards, however long the gap. So:

1. **Find out which source and why.** On GitHub, open the "Actions" tab, click
   the failed run, then the step "Fetch new rates". The last lines name the
   source and the error.
2. **Check whether it is temporary.** Open the bank's page (links in
   "Sources" below). If the site is down, do nothing: wait for the next runs.
   To test from GitHub's servers, go to Actions > "Test de connexion" >
   "Run workflow". To test from your Mac, run `python3 update.py`.
3. **If it stays broken for more than a day or two,** the bank probably
   changed its address or its file layout. The code for each bank is in its
   own file: `fxrates/banque_de_france.py`, `fxrates/uae.py`,
   `fxrates/argentina.py`, `fxrates/colombia.py`. Save a new sample answer in
   `tests/fixtures/`, fix the code, run the checks, and push. The next update
   fills the gap.
4. **Colombia only:** if the error mentions a certificate, the bank's
   server may have changed its security certificates. The extra certificate
   in `fxrates/certificates/` is valid until 2030.

**Conflicts.** If a bank changes a rate already saved, the saved value is
kept and a "Conflit" message appears. If the new value is the right one,
change it by hand in `data/rates.csv`, delete that conflict from the
`"conflicts"` list in `data/status.json`, and push. The next update rebuilds
`data/export_all.csv`.

## If the automatic updates stop

Check it on the page ("Dernière mise à jour" is more than a day old) or in
the "Actions" tab on GitHub (no new run of "Mise à jour des taux").

- **GitHub switched the schedule off.** On public projects, GitHub turns off
  scheduled runs after 60 days with no activity in the project. The robot's
  own saves should keep it active, but if it happens, the Actions tab shows a
  message. To restart: Actions > "Mise à jour des taux" > **"Enable
  workflow"**, then **"Run workflow"** to catch up at once. From the
  terminal: `gh workflow enable update.yml` then `gh workflow run update.yml`.
- **A run fails every time.** See "If a source breaks" above.
- **Runs start a little late.** Normal: GitHub can delay scheduled runs when
  it is busy, sometimes by up to an hour.

You can start an update at any time: Actions > "Mise à jour des taux" >
"Run workflow".

**GitHub's machine version.** Both workflows run on `ubuntu-24.04`, a fixed
version, so a GitHub upgrade cannot change them without warning. GitHub
announces when it will retire a version, months ahead. Then change
`runs-on: ubuntu-24.04` to the newer version in both files in
`.github/workflows/`, push, and use "Run workflow" on both to check.

---

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
