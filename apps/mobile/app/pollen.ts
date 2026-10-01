// TASK-8.8 / ADR-020: presentation of the backend's per-area `pollen` block
// (dashboard.py, TASK-8.9). The numbers are a CAMS MODEL FORECAST, not a pollen-trap
// measurement (rule #7) - every string here says so. Freshness is the server's own
// value (rule #8), never recomputed from the clock; missing is "brak danych", never 0.

import type { Freshness } from "./freshness";

export type PollenSpecies = "alder" | "birch" | "grass" | "mugwort" | "ragweed";
export type PollenValues = Record<PollenSpecies, number | null>;
// UNAVAILABLE = no snapshot for the area / source never succeeded (ADR-012).
export type PollenFreshness = Freshness | "UNAVAILABLE";

// Contract of dashboard.py `pollen` (= one /pollen/latest area + source fields).
export type PollenBlock = {
  source: string;
  attribution: string;
  kind: "model_forecast";
  model: string | null;
  unit: string | null;
  forecast_reference_time: string | null;
  fetched_at: string | null;
  freshness: PollenFreshness;
  valid_at: string | null;
  current: PollenValues | null;
  days: { date: string; max: PollenValues }[];
  source_status: { freshness: PollenFreshness; last_success_at: string | null };
};

export const POLLEN_SPECIES: PollenSpecies[] = ["alder", "birch", "grass", "mugwort", "ragweed"];

export const POLLEN_NAME: Record<PollenSpecies, string> = {
  alder: "Olcha",
  birch: "Brzoza",
  grass: "Trawy",
  mugwort: "Bylica",
  ragweed: "Ambrozja",
};

export type PollenLevel = "BELOW_SEASON" | "SEASON" | "PEAK";

export const POLLEN_LEVEL_LABEL: Record<PollenLevel, string> = {
  BELOW_SEASON: "poniżej progu sezonu",
  SEASON: "sezon pylenia",
  PEAK: "szczyt pylenia",
};

// Verified 2026-10-01 (ADR-020): EEA Climate-ADAPT "CAMS pollen viewer" - "For alder,
// birch, olive and mugwort, concentrations >= 10 pollen/m3 demarcate the pollen season
// and >= 100 pollen/m3 the peak pollen period (Pfaar et al., 2017). For grass and
// ragweed, >= 3 ... season and >= 50 ... peak (Pfaar et al., 2017, 2020)" (EAACI).
// These are SEASON/PEAK demarcations, not symptom-risk classes - labelled as such.
// Applied only to unit "grains/m³" (no conversion, ADR-016 style).
export const POLLEN_THRESHOLD_UNIT = "grains/m³";
export const POLLEN_THRESHOLDS: Record<PollenSpecies, { season: number; peak: number }> = {
  alder: { season: 10, peak: 100 },
  birch: { season: 10, peak: 100 },
  mugwort: { season: 10, peak: 100 },
  grass: { season: 3, peak: 50 },
  ragweed: { season: 3, peak: 50 },
};

export const POLLEN_TITLE = "Pyłki — prognoza modelu CAMS (nie pomiar)";
export const POLLEN_NOTE =
  "Prognoza modelowa, niezwalidowana przez dostawcę. Progi (EAACI, wg CAMS/EEA) wyznaczają sezon i szczyt pylenia, nie ryzyko objawów.";

export function pollenLevel(
  species: PollenSpecies,
  value: number | null,
  unit: unknown,
): PollenLevel | null {
  if (value === null || !Number.isFinite(value) || value < 0 || unit !== POLLEN_THRESHOLD_UNIT) {
    return null;
  }
  const t = POLLEN_THRESHOLDS[species];
  return value >= t.peak ? "PEAK" : value >= t.season ? "SEASON" : "BELOW_SEASON";
}

export type PollenLine = {
  species: PollenSpecies;
  name: string;
  text: string;
  level: PollenLevel | null;
};

export type PollenView = {
  title: string;
  // ok = FRESH; recent = RECENT (values shown, age flagged); stale/unavailable = no values.
  state: "ok" | "recent" | "stale" | "unavailable";
  status: string | null; // explicit line for recent/stale/unavailable
  lines: PollenLine[]; // empty unless ok/recent
  fetchedAt: string | null; // ISO, for the component to format
  validAt: string | null; // ISO hour the values are for (block.valid_at)
  note: string;
  attribution: string;
};

const isObject = (x: unknown): x is Record<string, unknown> =>
  typeof x === "object" && x !== null && !Array.isArray(x);

const RANK: PollenFreshness[] = ["FRESH", "RECENT", "STALE", "UNAVAILABLE"];

// Unknown/garbage -> UNAVAILABLE (fail safe: never a falsely fresh label).
function asFreshness(f: unknown): PollenFreshness {
  return RANK.includes(f as PollenFreshness) ? (f as PollenFreshness) : "UNAVAILABLE";
}

// Area data AND source can each be stale (ADR-012): the worse one wins.
export function effectiveFreshness(block: Record<string, unknown>): PollenFreshness {
  const own = asFreshness(block.freshness);
  const src = asFreshness(
    isObject(block.source_status) ? block.source_status.freshness : undefined,
  );
  return RANK[Math.max(RANK.indexOf(own), RANK.indexOf(src))];
}

// The number the user reads: level and text both derive from THIS, so "10" is never
// shown next to "poniżej progu sezonu" (9,96 displays as 10 -> season).
export function roundPollen(v: number): number {
  return v >= 10 ? Math.round(v) : Math.round(v * 10) / 10;
}

export function formatPollenValue(v: number): string {
  return String(roundPollen(v)).replace(".", ",");
}

function lineFor(
  species: PollenSpecies,
  current: Record<string, unknown>,
  unit: unknown,
): PollenLine {
  const raw = current[species];
  const name = POLLEN_NAME[species];
  if (typeof raw !== "number" || !Number.isFinite(raw) || raw < 0) {
    return { species, name, text: "brak danych", level: null };
  }
  const level = pollenLevel(species, roundPollen(raw), unit);
  const u = typeof unit === "string" && unit !== "" ? ` ${unit}` : "";
  const value = `${formatPollenValue(raw)}${u}`;
  return { species, name, text: level ? `${POLLEN_LEVEL_LABEL[level]} (${value})` : value, level };
}

// null = nothing to show (older backend without the field, or no attribution to credit).
export function pollenView(block: unknown): PollenView | null {
  if (!isObject(block) || typeof block.attribution !== "string" || block.attribution === "") {
    return null;
  }
  const fetchedAt = typeof block.fetched_at === "string" ? block.fetched_at : null;
  const validAt = typeof block.valid_at === "string" ? block.valid_at : null;
  const base = { title: POLLEN_TITLE, fetchedAt, validAt, note: POLLEN_NOTE, attribution: block.attribution };
  const freshness = effectiveFreshness(block);
  const current = isObject(block.current) ? block.current : null;

  if (freshness === "UNAVAILABLE" || (freshness !== "STALE" && current === null)) {
    return { ...base, state: "unavailable", status: "Brak danych o pyłkach.", lines: [] };
  }
  if (freshness === "STALE") {
    return {
      ...base,
      state: "stale",
      status: "Dane o pyłkach są nieaktualne — nie pokazujemy poziomów.",
      lines: [],
    };
  }
  const lines = POLLEN_SPECIES.map((s) => lineFor(s, current ?? {}, block.unit));
  return {
    ...base,
    state: freshness === "RECENT" ? "recent" : "ok",
    status: freshness === "RECENT" ? "Dane niedawne — prognoza mogła się już zmienić." : null,
    lines,
  };
}
