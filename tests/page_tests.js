// Checks for the page logic in app.js. Used by two runners:
//   tests/test_page.py  (automatic, Apple's JavaScript engine via osascript)
//   tests/page_test.html (open it in any browser through the local server)
//
// runPageTests returns { failures: [...], downloads: { "start_end": csv text } }.
// `downloads` is the exact text the page would download for each range, so the
// runners can compare it byte for byte with export_csv.py and the reference file.

"use strict";

function runPageTests(FX, exportText, delimiter, ranges) {
  const failures = [];
  function check(name, actual, expected) {
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {
      failures.push(`${name}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
    }
  }

  check("toIso", FX.toIso("30/09/2026"), "2026-09-30");
  check("toFr", FX.toFr("2026-09-30"), "30/09/2026");
  check("daysBetween", FX.daysBetween("2026-09-28", "2026-10-02"), 4);

  const sample = FX.parseExport("Date;CHF;COP\r\n01/09/2026;0.9394;3726.91961\r\n02/09/2026;;3691.3704\r\n", ";");
  check("header", sample.header, "Date;CHF;COP");
  check("rows oldest first", sample.rows.map(r => r.iso), ["2026-09-01", "2026-09-02"]);
  check("empty cell stays empty", sample.rows[1].cells, ["02/09/2026", "", "3691.3704"]);
  check("range of one day", FX.selectRows(sample.rows, "2026-09-01", "2026-09-01").map(r => r.iso), ["2026-09-01"]);
  check("range outside the data", FX.selectRows(sample.rows, "2026-10-01", "2026-10-31"), []);
  check("csv format", FX.buildCsv(sample.header, sample.rows.slice(1)),
        "Date;CHF;COP\r\n02/09/2026;;3691.3704\r\n");
  check("last complete month", FX.lastCompleteMonth("2026-10-07"), ["2026-09-01", "2026-09-30"]);
  check("last complete month in January", FX.lastCompleteMonth("2027-01-15"), ["2026-12-01", "2026-12-31"]);
  check("last complete month, leap February", FX.lastCompleteMonth("2028-03-01"), ["2028-02-01", "2028-02-29"]);
  check("last complete month, 31 days", FX.lastCompleteMonth("2026-08-31"), ["2026-07-01", "2026-07-31"]);

  const status = {
    sources: { "Banque de France": { ok: false, currencies: ["CHF"] }, "BCRA": { ok: true, currencies: ["ARS"] } },
    latest: { CHF: "2026-09-25", ARS: "2026-09-30", COP: null },
    conflicts: [{ date: "2026-09-01", currency: "USD", stored: "1.159", source_now: "1.16" }],
    flags: [
      { date: "2026-09-02", kind: "big_move", message: "variation dans la période" },
      { date: "2026-09-03", kind: "aed_usd_peg", message: "écart AED dans la période" },
      { date: "2026-09-04", kind: "zero_or_negative", message: "taux nul dans la période" },
      { date: "2026-09-07", kind: "missing_weekday", message: "jour férié : pas affiché" },
      { date: "2026-09-05", kind: "missing_day", message: "COP manquant : pas affiché" },
      { date: "2026-08-31", kind: "big_move", message: "hors période" },
    ],
  };
  check("banner warnings", FX.warnings(status, 4, "2026-10-01"), [
    "La dernière mise à jour de la source « Banque de France » a échoué (CHF) : les taux récents peuvent manquer.",
    "Les derniers taux CHF datent du 25/09/2026 (plus de 4 jours).",
    "Aucun taux disponible pour COP.",
    "Conflit : la source indique maintenant 1,16 pour USD le 01/09/2026. La valeur enregistrée, 1,159, est conservée.",
  ]);
  check("no banner when all is fine",
        FX.warnings({ sources: {}, latest: { ARS: "2026-09-30" }, conflicts: [] }, 4, "2026-10-01"), []);
  check("only serious alerts, only for the chosen range, plus conflicts",
        FX.alerts(status, "2026-09-01", "2026-09-30"), [
          "variation dans la période", "écart AED dans la période", "taux nul dans la période",
          "Conflit : la source indique maintenant 1,16 pour USD le 01/09/2026. La valeur enregistrée, 1,159, est conservée.",
        ]);
  check("no conflict outside the range", FX.alerts(status, "2026-09-02", "2026-09-30").length, 3);

  // The real data: what the page would download for each range.
  const data = FX.parseExport(exportText, delimiter);
  const downloads = {};
  for (const [start, end] of ranges) {
    downloads[`${start}_${end}`] = FX.buildCsv(data.header, FX.selectRows(data.rows, start, end));
  }
  return { failures, downloads };
}
