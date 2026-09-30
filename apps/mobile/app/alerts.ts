// TASK-7.2: nationwide IMGW alerts from the dashboard aggregate. Texts are shown
// verbatim from the source (rule #10) - nothing here classifies or rewrites them.
import type { Freshness } from "./freshness";

export type AlertItem = {
  external_id: string;
  event_type: string;
  severity_raw: string;
  issuing_office: string;
  description: string;
  areas: Record<string, unknown>[];
  valid_until: string;
  fetched_at: string;
  freshness: Freshness;
};

export type SourceFreshness = Freshness | "UNAVAILABLE";

export type AlertsBlock = {
  scope: "national";
  source: string;
  attribution: string;
  items: AlertItem[];
  // ADR-012: per alert source - when did we last fetch it successfully.
  source_status: Record<string, { freshness: SourceFreshness; last_success_at: string | null }>;
};

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

export function summarizeAlerts(block: AlertsBlock): AlertsSummary {
  const statuses = Object.entries(block.source_status);
  const unhealthy = statuses.filter(
    ([, s]) => s.freshness !== "FRESH" && s.freshness !== "RECENT",
  );
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

// Unique voivodeship names from the raw `areas` objects; anything that isn't a
// non-empty string is skipped rather than guessed (areas are unnormalized raw
// source JSON, ADR-009).
export function alertAreasLabel(areas: Record<string, unknown>[]): string {
  const names = areas
    .map((area) => area.wojewodztwo)
    .filter((name): name is string => typeof name === "string" && name.length > 0);
  return [...new Set(names)].join(", ");
}
