// Home keeps at most two lines about warnings (the lists live on the Alerts tab). They may
// only say what the summaries allow (ADR-012): silent for a confirmed all-clear, a real
// warning for a current list, a neutral caveat when a source is silent or old. A missing
// banner must never be readable as "no alerts" - so a missing/failed block gets a neutral
// banner too (the caller passes `null` once loading has finished without data).
import type { AlertsSummary } from "./alerts";
import type { HydroSummary } from "./hydro";

export type HomeBanner = { tone: "danger" | "warning" | "neutral"; text: string };

export function homeAlertsBanner(summary: AlertsSummary | null, count: number): HomeBanner | null {
  if (summary === null) return { tone: "neutral", text: "Ostrzeżenia chwilowo niedostępne." };
  switch (summary.kind) {
    case "list":
      return { tone: "warning", text: `Ostrzeżenia hydrologiczne w Polsce: ${count}. Zobacz listę.` };
    case "list-maybe-outdated":
      return { tone: "warning", text: "Lista ostrzeżeń może być nieaktualna. Zobacz szczegóły." };
    case "unavailable":
      return { tone: "neutral", text: "Ostrzeżenia chwilowo niedostępne." };
    default:
      return null;
  }
}

// `summary` must be built with an unlimited list (summarizeHydro(block, now, Infinity)) so the
// counts are complete. Only CURRENT stations count (FRESH/RECENT and a healthy source); an
// old or silent reading degrades to a neutral line, never to calm. `null` = no data / failed.
export function homeHydroBanner(summary: HydroSummary | null): HomeBanner | null {
  const unavailable: HomeBanner = { tone: "neutral", text: "Stany wody chwilowo niedostępne." };
  if (summary === null || summary.kind === "unavailable") return unavailable;
  if (summary.kind === "none-confirmed") return null;
  const outdated: HomeBanner = {
    tone: "neutral",
    text: "Dane o stanach wody mogą być nieaktualne. Zobacz zakładkę Alerty.",
  };
  if (summary.outdated) return outdated;
  const current = summary.items.filter(({ freshness }) => freshness === "FRESH" || freshness === "RECENT");
  const alarms = current.filter(({ station }) => station.status === "ALARM").length;
  const warnings = current.length - alarms;
  if (alarms > 0) return { tone: "danger", text: `Stan alarmowy na stacjach wody: ${alarms}. Zobacz listę.` };
  if (warnings > 0) return { tone: "warning", text: `Stan ostrzegawczy na stacjach wody: ${warnings}. Zobacz listę.` };
  return outdated;
}
