// TASK-9.7: structure of the Alerts tab (S2) and the detail screen (S3). Pure logic.
// Alert texts are the source's own, verbatim (rule #10); nothing here classifies or rewrites
// them. The location split comes from the backend (`local_alerts`, `geo_match`, ADR-013):
// `voivodeship` = applies to the chosen area, `unresolved` = we cannot tell and it is SHOWN,
// never hidden. An all-clear is claimed only while the alert source is healthy (ADR-012).
import { type AlertItem, type AlertsBlock, alertKey, summarizeAlerts } from "./alerts";

export type LocalStatus =
  | "has-local" // at least one alert applies to the chosen area
  | "none-confirmed" // healthy source, nothing applies, nothing unresolved
  | "unknown"; // source silent/old, or the last refresh failed: no claim

export type AlertsScreenModel = {
  localStatus: LocalStatus;
  local: AlertItem[];
  unresolved: AlertItem[];
  // National alerts that are neither local nor unresolved: "elsewhere in Poland".
  elsewhere: AlertItem[];
  // false = the backend sent no `local_alerts` (older backend): only the national list exists
  // and the screen must say it is not matched to the location.
  located: boolean;
};

export const LOCAL_NONE_TEXT = "Brak aktywnych ostrzeżeń dla Twojego województwa";
export const LOCAL_UNKNOWN_TEXT = "Nie udało się sprawdzić ostrzeżeń";
export const UNRESOLVED_NOTE = "Nie da się ustalić, czy to ostrzeżenie dotyczy Twojej lokalizacji. Sprawdź obszary w treści.";
export const NATIONAL_UNMATCHED_NOTE = "Cała Polska — lista nie jest dopasowana do Twojej lokalizacji.";

export function buildAlertsScreen(
  national: AlertsBlock,
  localAlerts: AlertItem[] | null | undefined,
  now: number,
  refreshFailed: boolean,
): AlertsScreenModel {
  const summary = summarizeAlerts(national, now);
  const healthy = !refreshFailed && (summary.kind === "list" || summary.kind === "none-confirmed");
  if (!Array.isArray(localAlerts)) {
    return { localStatus: "unknown", local: [], unresolved: [], elsewhere: national.items, located: false };
  }
  const local = localAlerts.filter((a) => a.geo_match === "voivodeship");
  const unresolved = localAlerts.filter((a) => a.geo_match !== "voivodeship");
  const taken = new Set(localAlerts.map(alertKey));
  const elsewhere = national.items.filter((a) => !taken.has(alertKey(a)));
  const localStatus: LocalStatus =
    local.length > 0 ? "has-local" : healthy && unresolved.length === 0 ? "none-confirmed" : "unknown";
  return { localStatus, local, unresolved, elsewhere, located: true };
}

// Detail lookup by the key the list put into the route. National and local copies of one alert
// share the key; the local copy (with `geo_match`) wins.
export function findAlert(key: string | undefined, local: AlertItem[] | null | undefined, national: AlertItem[] | undefined): AlertItem | null {
  if (!key) return null;
  return (local ?? []).find((a) => alertKey(a) === key) ?? (national ?? []).find((a) => alertKey(a) === key) ?? null;
}

export const GEO_MATCH_TEXT: Record<string, string> = {
  voivodeship: "Dotyczy Twojego województwa",
  unresolved: "Nie da się ustalić, czy dotyczy Twojej lokalizacji",
};

// "Obszary" line: the source's own region names as sent; nothing is guessed.
export function areaNames(areas: unknown): string[] {
  if (!Array.isArray(areas)) return [];
  const out = areas.flatMap((a) => {
    const r = a as Record<string, unknown> | null;
    return r && typeof r.wojewodztwo === "string" && r.wojewodztwo.trim() !== "" ? [r.wojewodztwo.trim()] : [];
  });
  return [...new Set(out)];
}
