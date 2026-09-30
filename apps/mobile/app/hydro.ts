// TASK-7.2 (hydrology part): nationwide IMGW water-level stations in WARNING/ALARM.
// Statuses come from the backend (app/api/v1/hydro.py compares IMGW's own published
// thresholds) - nothing here classifies a level (rule #10). This module only decides
// WHAT THE SECTION MAY CLAIM, so stale data never reads as "all clear" (rule #8).
import type { SourceFreshness } from "./alerts";

export type HydroStatus = "NORMAL" | "WARNING" | "ALARM" | "UNKNOWN";

export type HydroStation = {
  station_id: string;
  station_name: string;
  latitude: number;
  longitude: number;
  water_level_cm: number;
  warning_level_cm: number | null;
  alarm_level_cm: number | null;
  status: HydroStatus;
  unit: string;
  observed_at: string;
  freshness: SourceFreshness;
  source: string;
};

export type HydroBlock = {
  stations: HydroStation[];
  attribution: string;
  // ADR-012: when did the scheduler last fetch IMGW hydro successfully.
  source_status: { freshness: SourceFreshness; last_success_at: string | null };
};

export const HYDRO_LIST_LIMIT = 5;

// Same thresholds as FRESH_MAX_AGE/RECENT_MAX_AGE in app/api/v1/hydro.py. Duplicated
// on purpose: the screen doesn't refresh itself, so a label the server computed at
// fetch time must be aged against Date.now() here (PR #59/#61 lesson).
const FRESH_MAX_MS = 2 * 60 * 60 * 1000;
const RECENT_MAX_MS = 6 * 60 * 60 * 1000;

const RANK: Record<SourceFreshness, number> = { FRESH: 0, RECENT: 1, STALE: 2, UNAVAILABLE: 3 };

export const HYDRO_FRESHNESS_LABEL: Record<SourceFreshness, string> = {
  FRESH: "świeże",
  RECENT: "niedawne",
  STALE: "nieaktualne",
  UNAVAILABLE: "brak danych",
};

export const HYDRO_STATUS_LABEL: Record<HydroStatus, string> = {
  ALARM: "STAN ALARMOWY",
  WARNING: "STAN OSTRZEGAWCZY",
  NORMAL: "poniżej progów",
  UNKNOWN: "brak progów IMGW",
};

function valid(f: unknown): SourceFreshness {
  return typeof f === "string" && f in RANK ? (f as SourceFreshness) : "UNAVAILABLE";
}

function worst(a: SourceFreshness, b: SourceFreshness): SourceFreshness {
  return RANK[a] >= RANK[b] ? a : b;
}

const healthy = (f: SourceFreshness) => f === "FRESH" || f === "RECENT";

// Missing/unparsable timestamp degrades to UNAVAILABLE instead of throwing.
export function ageFreshness(iso: unknown, now: number): SourceFreshness {
  const t = typeof iso === "string" ? Date.parse(iso) : Number.NaN;
  if (Number.isNaN(t)) return "UNAVAILABLE";
  const age = now - t;
  if (age <= FRESH_MAX_MS) return "FRESH";
  if (age <= RECENT_MAX_MS) return "RECENT";
  return "STALE";
}

// Server label (as of fetch) or the age at `now`, whichever is worse.
export function stationFreshness(s: HydroStation, now: number): SourceFreshness {
  return worst(valid(s.freshness), ageFreshness(s.observed_at, now));
}

export type HydroItem = { station: HydroStation; freshness: SourceFreshness };

export type HydroSummary =
  | { kind: "list"; items: HydroItem[]; more: number; outdated: boolean; lastSuccessAt: string | null }
  | { kind: "none-confirmed"; unassessed: number }
  | { kind: "unavailable"; lastSuccessAt: string | null };

export function summarizeHydro(block: HydroBlock, now: number, limit = HYDRO_LIST_LIMIT): HydroSummary {
  const stations = Array.isArray(block.stations) ? block.stations : [];
  const status = block.source_status;
  const lastSuccessAt = typeof status?.last_success_at === "string" ? status.last_success_at : null;
  const sourceOk = healthy(worst(valid(status?.freshness), ageFreshness(lastSuccessAt, now)));

  // UNKNOWN is never "OK" and never listed; an unrecognised status is ignored, not guessed.
  const active = stations
    .filter((s) => s.status === "ALARM" || s.status === "WARNING")
    .sort(
      (a, b) =>
        Number(b.status === "ALARM") - Number(a.status === "ALARM") ||
        (a.station_name < b.station_name ? -1 : a.station_name > b.station_name ? 1 : 0) ||
        (a.station_id < b.station_id ? -1 : a.station_id > b.station_id ? 1 : 0),
    );

  if (active.length > 0) {
    return {
      kind: "list",
      items: active.slice(0, limit).map((station) => ({ station, freshness: stationFreshness(station, now) })),
      more: Math.max(0, active.length - limit),
      outdated: !sourceOk,
      lastSuccessAt,
    };
  }
  // "No warning/alarm stations" only with a healthy source AND at least one current reading.
  if (sourceOk && stations.some((s) => healthy(stationFreshness(s, now)))) {
    return { kind: "none-confirmed", unassessed: stations.filter((s) => s.status !== "NORMAL").length };
  }
  return { kind: "unavailable", lastSuccessAt };
}

// Thresholds are IMGW's own numbers, shown for context only.
export function hydroLevelLine(s: HydroStation): string {
  const parts = [`${s.water_level_cm} ${s.unit}`];
  if (s.warning_level_cm !== null) parts.push(`próg ostrzegawczy ${s.warning_level_cm} ${s.unit}`);
  if (s.alarm_level_cm !== null) parts.push(`alarmowy ${s.alarm_level_cm} ${s.unit}`);
  return parts.join(" · ");
}
