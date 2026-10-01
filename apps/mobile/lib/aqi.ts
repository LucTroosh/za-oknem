// TASK-4.2 / ADR-015: presentation of the backend's European AQI block (`air.index`).
// The index is computed server-side (app/air_index.py, EEA bands) - nothing here
// classifies a concentration (rule #10); this module only formats what the block says
// and decides what the badge may CLAIM, so missing/old data never reads as a confident
// "good" (rule #8).

import type { AirIndex } from "../../../packages/api-contract/schema";

// Types come from the generated contract (ADR-024); `valid_until` stays optional (older backend).
export type AqiLevel = NonNullable<AirIndex["level"]>; // level null = no index
export type AirIndexBlock = Pick<AirIndex, "level" | "complete" | "params" | "missing" | "dominant"> & {
  // ISO time after which the earliest contributing input turns STALE; null without index.
  valid_until?: string | null;
};

export type AirIndexView = {
  level: AqiLevel | null;
  // Level is never conveyed by colour alone: the label, the step and the icon all carry it.
  label: string;
  step: number | null; // 1..6 (EEA band number)
  icon: string;
  headline: string;
  detail: string | null;
  note: string | null;
};

// Order = EEA band order, worst last. English names are EEA's; the Polish labels are OUR
// translation (no verified official Polish names for the 2025 six-band scheme, ADR-015).
const LEVELS: AqiLevel[] = ["GOOD", "FAIR", "MODERATE", "POOR", "VERY_POOR", "EXTREMELY_POOR"];

export const AQI_LABEL: Record<AqiLevel, string> = {
  GOOD: "Dobra",
  FAIR: "Zadowalająca",
  MODERATE: "Umiarkowana",
  POOR: "Zła",
  VERY_POOR: "Bardzo zła",
  EXTREMELY_POOR: "Skrajnie zła",
};

const AQI_ICON: Record<AqiLevel, string> = {
  GOOD: "✓",
  FAIR: "✓",
  MODERATE: "!",
  POOR: "✕",
  VERY_POOR: "✕",
  EXTREMELY_POOR: "✕",
};

export const AQI_DISCLAIMER = "Europejski Indeks Jakości Powietrza (EEA), liczony z pomiarów GIOŚ.";

const STATUS_LABEL: Record<string, string> = {
  MISSING: "brak",
  STALE: "nieaktualne",
  UNIT: "inna jednostka",
  INVALID: "błędne",
};

const isObject = (x: unknown): x is Record<string, unknown> =>
  typeof x === "object" && x !== null && !Array.isArray(x);

export function validAqiLevel(l: unknown): AqiLevel | null {
  return typeof l === "string" && (LEVELS as string[]).includes(l) ? (l as AqiLevel) : null;
}

export function aqiStep(level: AqiLevel): number {
  return LEVELS.indexOf(level) + 1;
}

// "NO2 (brak), O3 (nieaktualne)"; "" for garbage or nothing missing.
export function aqiGaps(missing: unknown): string {
  if (!isObject(missing)) return "";
  return Object.entries(missing)
    .map(([code, status]) => `${code} (${STATUS_LABEL[String(status)] ?? "brak"})`)
    .join(", ");
}

function isExpired(validUntil: unknown, now: number, receivedAt: number, maxAgeMs: number): boolean {
  const t = typeof validUntil === "string" ? Date.parse(validUntil) : Number.NaN;
  return Number.isNaN(t) ? now - receivedAt > maxAgeMs : now > t;
}

// Same fallback as the outdoor verdict when `valid_until` is unusable.
export const AQI_FALLBACK_MAX_AGE_MS = 60 * 60 * 1000;

function noIndex(detail: string | null, note: string | null): AirIndexView {
  return {
    level: null,
    label: "Brak indeksu",
    step: null,
    icon: "?",
    headline: "Indeks jakości powietrza: brak indeksu",
    detail,
    note,
  };
}

// null = nothing to show (older backend without the field, or not an object): the badge
// disappears instead of inventing a value. `receivedAt` = device time of the response.
export function airIndexView(block: unknown, now: number, receivedAt: number): AirIndexView | null {
  if (!isObject(block)) return null;
  const level = validAqiLevel(block.level);
  const gaps = aqiGaps(block.missing);
  if (level === null) {
    return noIndex(gaps === "" ? "brak danych" : `brak danych: ${gaps}`, AQI_DISCLAIMER);
  }
  if (isExpired(block.valid_until, now, receivedAt, AQI_FALLBACK_MAX_AGE_MS)) {
    return noIndex("dane mogły się zestarzeć, odśwież widok", AQI_DISCLAIMER);
  }
  const label = AQI_LABEL[level];
  const complete = block.complete === true;
  const dominant = Array.isArray(block.dominant)
    ? block.dominant.filter((d): d is string => typeof d === "string")
    : [];
  return {
    level,
    label,
    step: aqiStep(level),
    icon: AQI_ICON[level],
    // An incomplete set is only a lower bound: an absent pollutant could be worse.
    headline: `Indeks jakości powietrza: ${complete ? "" : "co najmniej "}${label.toLowerCase()}`,
    detail: dominant.length > 0 ? `decyduje: ${dominant.join(", ")}` : null,
    note: complete
      ? AQI_DISCLAIMER
      : `${AQI_DISCLAIMER} Niepełny zestaw zanieczyszczeń${gaps === "" ? "" : `: ${gaps}`}.`,
  };
}
