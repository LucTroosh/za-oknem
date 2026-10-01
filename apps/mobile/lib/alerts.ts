// TASK-7.2: nationwide IMGW alerts from the dashboard aggregate. Texts are shown
// verbatim from the source (rule #10) - nothing here classifies or rewrites them.
import type { AlertOut, DashboardAlerts, SourceStatusOut } from "../../../packages/api-contract/schema";

// Types derive from the generated contract (ADR-024); only the fields this screen reads are
// required, so a drift in them fails `tsc` while extra server fields are ignored.
export type AlertItem = Pick<
  AlertOut,
  | "external_id"
  | "source"
  | "published_at"
  | "event_type"
  | "severity_raw"
  | "issuing_office"
  | "description"
  | "areas"
  | "valid_until"
  | "fetched_at"
  | "freshness"
>;

export type SourceFreshness = SourceStatusOut["freshness"];

// ADR-012: `source_status` = per alert source, when did we last fetch it successfully.
export type AlertsBlock = Omit<DashboardAlerts, "items"> & { items: AlertItem[] };

const SOURCE_LABEL: Record<string, string> = {
  imgw_warningshydro: "IMGW – ostrzeżenia hydrologiczne",
};

// What the alerts section may claim (ADR-012). An empty list is a confirmed
// "no alerts" ONLY when every source is FRESH/RECENT; otherwise the source is
// silent, and saying "brak ostrzeżeń" would be a false all-clear.
export type AlertsSummary =
  | { kind: "list" }
  | { kind: "list-maybe-outdated"; lastSuccessAt: string | null }
  | { kind: "none-confirmed"; sources: string[] }
  | { kind: "unavailable"; lastSuccessAt: string | null };

// Same bound as the server's alert RECENT_MAX_AGE (api/v1/alerts.py, 6h). The
// server's freshness is computed once per response, but this screen stays open
// (or is resumed from background) for hours without refetching - so a status
// that was FRESH at fetch time must stop counting as healthy once it ages past
// this bound on the device clock. Only ever downgrades, never upgrades.
const MAX_HEALTHY_AGE_MS = 6 * 60 * 60 * 1000;

function isHealthy(
  s: { freshness: SourceFreshness; last_success_at: string | null },
  now: number,
): boolean {
  if (s.freshness !== "FRESH" && s.freshness !== "RECENT") return false;
  const last = s.last_success_at === null ? NaN : Date.parse(s.last_success_at);
  return Number.isFinite(last) && now - last <= MAX_HEALTHY_AGE_MS;
}

export function summarizeAlerts(block: AlertsBlock, now: number = Date.now()): AlertsSummary {
  // `?? {}`: an older API without source_status must degrade to "unavailable",
  // not throw and take the whole Home screen down (rule #1, client side).
  const statuses = Object.entries(block.source_status ?? {});
  const unhealthy = statuses.filter(([, s]) => !isHealthy(s, now));
  // No sources listed at all can't confirm anything either.
  const healthy = statuses.length > 0 && unhealthy.length === 0;
  // Oldest last success among unhealthy sources; one never-fetched source -> null.
  // ISO strings from the server share one format/offset, so string order = time order.
  const times = unhealthy.map(([, s]) => s.last_success_at);
  const oldest = times.includes(null) ? null : ((times as string[]).sort()[0] ?? null);
  if (block.items.length > 0) {
    return healthy ? { kind: "list" } : { kind: "list-maybe-outdated", lastSuccessAt: oldest };
  }
  if (healthy) {
    return {
      kind: "none-confirmed",
      sources: statuses.map(([id]) => SOURCE_LABEL[id] ?? id),
    };
  }
  return { kind: "unavailable", lastSuccessAt: oldest };
}

// external_id is only unique per source and revision (DB identity is
// source_id + source_record_id), so a React key needs all three (Codex review).
export function alertKey(alert: AlertItem): string {
  return `${alert.source}:${alert.external_id}:${alert.published_at}`;
}

// Unique voivodeship names from the raw `areas` objects; anything that isn't a
// non-empty string is skipped rather than guessed (areas are unnormalized raw
// source JSON, ADR-009).
export function alertAreasLabel(areas: Record<string, unknown>[]): string {
  const names = areas
    .map((area) => area.wojewodztwo)
    .filter((name): name is string => typeof name === "string" && name.length > 0);
  return [...new Set(names)].join(", ");
}
