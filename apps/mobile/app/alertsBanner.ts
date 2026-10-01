// Home keeps one line about alerts (the list itself lives on the Alerts tab). It may only
// say what summarizeAlerts allows (ADR-012): nothing when "no alerts" is confirmed (Home
// stays quiet), a warning for a real list, a caveat when the source is silent or old.
import type { AlertsSummary } from "./alerts";

export type HomeBanner = { tone: "warning" | "neutral"; text: string } | null;

export function homeAlertsBanner(summary: AlertsSummary, count: number): HomeBanner {
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
