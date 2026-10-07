// Logic of the FX rates page. Plain JavaScript, no libraries.
//
// The page reads three files:
//   settings.json         the CSV delimiter and the "stale after N days" setting
//   data/export_all.csv   the whole history, already in the final CSV format
//                         (written by the Python exporter, fxrates/export.py)
//   data/status.json      last update time, source failures, conflicts and flags
//
// The page never formats a number itself: it cuts the chosen date range out of
// data/export_all.csv. So the table and the downloaded file are exactly what
// export_csv.py produces.

"use strict";

// Alert kinds shown under the table. Holidays (missing_weekday, missing_day)
// are left out on purpose: only serious alerts are shown.
const SERIOUS_FLAGS = ["big_move", "aed_usd_peg", "zero_or_negative"];

const FX = {
  // "30/09/2026" -> "2026-09-30" (ISO dates compare correctly as text)
  toIso(frDate) {
    const [d, m, y] = frDate.split("/");
    return `${y}-${m}-${d}`;
  },

  // "2026-09-30" -> "30/09/2026"
  toFr(iso) {
    const [y, m, d] = iso.split("-");
    return `${d}/${m}/${y}`;
  },

  // First and last day of the last complete month (the month before the given ISO date).
  lastCompleteMonth(todayIso) {
    const [y, m] = todayIso.split("-").map(Number);
    const year = m === 1 ? y - 1 : y;
    const month = m === 1 ? 12 : m - 1;
    const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();  // day 0 of next month
    const mm = String(month).padStart(2, "0");
    return [`${year}-${mm}-01`, `${year}-${mm}-${lastDay}`];
  },

  // Whole days from ISO date a to ISO date b.
  daysBetween(a, b) {
    return Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
  },

  // Split the exported CSV into its header and rows (oldest first).
  parseExport(text, delimiter) {
    const lines = text.split("\r\n");
    if (lines[lines.length - 1] === "") lines.pop();
    const header = lines.shift();
    const rows = lines.map(line => {
      const cells = line.split(delimiter);
      return { iso: FX.toIso(cells[0]), line, cells };
    });
    return { header, columns: header.split(delimiter), rows };
  },

  // Rows between two ISO dates, inclusive.
  selectRows(rows, startIso, endIso) {
    return rows.filter(row => row.iso >= startIso && row.iso <= endIso);
  },

  // The CSV file: header, chosen rows, Windows line endings, no byte order mark.
  buildCsv(header, rows) {
    return [header, ...rows.map(row => row.line)].join("\r\n") + "\r\n";
  },

  // Serious alerts for the chosen range: large moves, AED gap, zero or
  // negative values, and conflicts (a source changed a stored rate).
  alerts(status, startIso, endIso) {
    const inRange = item => item.date >= startIso && item.date <= endIso;
    const messages = (status.flags || [])
      .filter(flag => inRange(flag) && SERIOUS_FLAGS.includes(flag.kind))
      .map(flag => flag.message);
    for (const c of (status.conflicts || []).filter(inRange)) messages.push(FX.conflictMessage(c));
    return messages;
  },

  conflictMessage(c) {
    return `Conflit : la source indique maintenant ${c.source_now.replace(".", ",")} pour ` +
      `${c.currency} le ${FX.toFr(c.date)}. La valeur enregistrée, ` +
      `${c.stored.replace(".", ",")}, est conservée.`;
  },

  // Warnings for the banner: failed sources, late currencies, conflicts.
  warnings(status, staleAfterDays, todayIso) {
    const messages = [];
    for (const [name, source] of Object.entries(status.sources || {})) {
      if (!source.ok) {
        messages.push(`La dernière mise à jour de la source « ${name} » a échoué ` +
          `(${source.currencies.join(", ")}) : les taux récents peuvent manquer.`);
      }
    }
    const lateByDate = {};
    for (const [cur, latest] of Object.entries(status.latest || {})) {
      if (!latest || FX.daysBetween(latest, todayIso) > staleAfterDays) {
        (lateByDate[latest] = lateByDate[latest] || []).push(cur);
      }
    }
    for (const [latest, currencies] of Object.entries(lateByDate)) {
      messages.push(latest === "null"
        ? `Aucun taux disponible pour ${currencies.join(", ")}.`
        : `Les derniers taux ${currencies.join(", ")} datent du ${FX.toFr(latest)} ` +
          `(plus de ${staleAfterDays} jours).`);
    }
    for (const c of status.conflicts || []) messages.push(FX.conflictMessage(c));
    return messages;
  },
};

// ---------------------------------------------------------------------------
// Page behaviour (only runs on the real page, not in the tests)

function todayIso() {
  const now = new Date();
  const pad = n => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

async function fetchText(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${path} : ${response.status}`);
  return response.text();
}

function showBanner(messages) {
  const banner = document.getElementById("bandeau");
  banner.replaceChildren();
  if (!messages.length) { banner.hidden = true; return; }
  const title = document.createElement("strong");
  title.textContent = "Attention :";
  const list = document.createElement("ul");
  for (const text of messages) {
    const item = document.createElement("li");
    item.textContent = text;
    list.append(item);
  }
  banner.append(title, list);
  banner.hidden = false;
}

async function startPage() {
  let settings, data, status;
  try {
    const [settingsText, exportText, statusText] = await Promise.all(
      ["settings.json", "data/export_all.csv", "data/status.json"].map(fetchText));
    settings = JSON.parse(settingsText);
    data = FX.parseExport(exportText, settings.csv_delimiter);
    status = JSON.parse(statusText);
  } catch (error) {
    showBanner(["Impossible de charger les données. Réessayez plus tard ou prévenez la personne " +
                "qui gère cette page."]);
    return;
  }

  const updated = document.getElementById("mise-a-jour");
  updated.textContent = "Dernière mise à jour : " + new Date(status.last_updated).toLocaleDateString("fr-FR");
  updated.hidden = false;
  showBanner(FX.warnings(status, settings.stale_after_days, todayIso()));

  const start = document.getElementById("debut");
  const end = document.getElementById("fin");
  const button = document.getElementById("telecharger");
  const message = document.getElementById("message");
  const frame = document.getElementById("cadre-tableau");
  const alertsBox = document.getElementById("alertes");
  const firstIso = data.rows[0].iso;
  const lastIso = data.rows[data.rows.length - 1].iso;
  let chosenRows = [];

  for (const input of [start, end]) {
    input.min = firstIso;  // only dates that exist in the data
    input.max = lastIso;
  }

  // The yellow box opens the calendar of the hidden date input, and shows its date as jj/mm/aaaa.
  for (const box of document.querySelectorAll(".date-affichee")) {
    const input = document.getElementById(box.dataset.pour);
    box.addEventListener("click", () => {
      try { input.showPicker(); } catch { input.focus(); }
    });
    input.addEventListener("change", () => {
      box.textContent = input.value ? FX.toFr(input.value) : box.dataset.vide;
      box.classList.toggle("vide", !input.value);
      refresh();
    });
  }

  function refresh() {
    chosenRows = [];
    frame.hidden = alertsBox.hidden = message.hidden = true;
    button.disabled = true;
    if (!start.value || !end.value) return;

    if (start.value < firstIso || end.value > lastIso) {
      message.textContent = `Choisissez des dates entre le ${FX.toFr(firstIso)} et le ${FX.toFr(lastIso)}.`;
      message.hidden = false;
      return;
    }
    if (start.value > end.value) {
      message.textContent = "La date de début doit être antérieure ou égale à la date de fin.";
      message.hidden = false;
      return;
    }

    chosenRows = FX.selectRows(data.rows, start.value, end.value);
    const head = document.createElement("tr");
    for (const name of data.columns) {
      const th = document.createElement("th");
      th.textContent = name;
      head.append(th);
    }
    const body = document.createDocumentFragment();
    for (const row of chosenRows) {
      const tr = document.createElement("tr");
      for (const cell of row.cells) {
        const td = document.createElement("td");
        td.textContent = cell;
        tr.append(td);
      }
      body.append(tr);
    }
    document.querySelector("#tableau thead").replaceChildren(head);
    document.querySelector("#tableau tbody").replaceChildren(body);
    frame.hidden = false;
    button.disabled = false;

    const alerts = FX.alerts(status, start.value, end.value);
    if (alerts.length) {
      alertsBox.open = false;
      alertsBox.querySelector("summary").textContent = `Alertes pour cette période : ${alerts.length}`;
      alertsBox.querySelector("ul").replaceChildren(...alerts.map(text => {
        const item = document.createElement("li");
        item.textContent = text;
        return item;
      }));
      alertsBox.hidden = false;
    }
  }

  button.addEventListener("click", () => {
    const blob = new Blob([FX.buildCsv(data.header, chosenRows)], { type: "text/csv;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `taux_de_change_${start.value}_${end.value}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);  // Safari needs a moment
  });

  document.getElementById("dernier-mois").addEventListener("click", () => {
    [start.value, end.value] = FX.lastCompleteMonth(todayIso());
    start.dispatchEvent(new Event("change"));
    end.dispatchEvent(new Event("change"));
  });
}

if (typeof document !== "undefined" && document.getElementById("tableau")) startPage();
