// TASK-7.2: nationwide IMGW alerts from the dashboard aggregate. Texts are shown
// verbatim from the source (rule #10) - nothing here classifies or rewrites them.
import type { Freshness } from "./freshness";

export type AlertItem = {
  external_id: string;
  source: string;
  published_at: string;
  event_type: string;
  severity_raw: string;
  issuing_office: string;
  description: string;
  areas: Record<string, unknown>[];
  valid_until: string;
  fetched_at: string;
  freshness: Freshness;
};

export type AlertsBlock = {
  scope: "national";
  source: string;
  attribution: string;
  items: AlertItem[];
};

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
