// TASK-7.3: one presentation path for dashboard `air` and `weather` readings. Values,
// units and server labels come from the backend block; this module only decides what a
// line may CLAIM (rule #8): a stale value reads as old (dimmed + age), a missing one as
// "brak danych" - never 0 (null != 0), never an old number that looks current.
import {
  type AgeBounds,
  FRESHNESS_LABEL,
  type FreshnessState,
  ageFreshness,
  ageLabel,
  asFreshness,
  worstFreshness,
} from "./freshness";

const HOUR = 60 * 60 * 1000;
// Mirror api/v1/air.py (2h/6h) and api/v1/weather.py (4h/8h), ADR-004.
export const AIR_AGE: AgeBounds = { freshMs: 2 * HOUR, recentMs: 6 * HOUR };
export const WEATHER_AGE: AgeBounds = { freshMs: 4 * HOUR, recentMs: 8 * HOUR };

export const NO_DATA = "brak danych";

// ok = FRESH; recent = RECENT (value shown, age flagged); stale = value dimmed and
// marked old; missing = no usable value.
export type LineState = "ok" | "recent" | "stale" | "missing";

export type ReadingLine = {
  key: string;
  label: string;
  text: string; // value with unit, or NO_DATA
  state: LineState;
  note: string | null; // "niedawne · 3 godz. temu" etc.
};

const isObject = (x: unknown): x is Record<string, unknown> =>
  typeof x === "object" && x !== null && !Array.isArray(x);

// Rounds first, then prints: -0.04 at 1 decimal is "0", never "-0" or "-0,0".
export function formatNumber(v: unknown, decimals: number): string | null {
  if (typeof v !== "number" || !Number.isFinite(v)) return null;
  const f = 10 ** decimals;
  return String(Math.round(v * f) / f).replace(".", ",");
}

export function withUnit(num: string, unit: unknown): string {
  if (typeof unit !== "string" || unit === "") return num;
  return unit === "%" || unit === "°" ? `${num}${unit}` : `${num} ${unit}`;
}

// Source level (ADR-012): `source_status` worse-of with its own age on the device clock.
// Absent (older backend) -> no extra constraint; each reading still carries its own label.
export type SourceState = { state: FreshnessState | null; lastSuccessAt: string | null };

export function sourceState(block: Record<string, unknown>, now: number, bounds: AgeBounds): SourceState {
  const s = block.source_status;
  if (!isObject(s)) return { state: null, lastSuccessAt: null };
  const last = typeof s.last_success_at === "string" ? s.last_success_at : null;
  const state =
    asFreshness(s.freshness) === "UNAVAILABLE"
      ? "UNAVAILABLE"
      : worstFreshness(s.freshness, ageFreshness(last, now, bounds));
  return { state, lastSuccessAt: last };
}

export type ReadingFormat = (value: number, unit: unknown) => string;

// One reading (`{value, unit, observed_at, freshness}`) -> a line. `format` returns the
// display text of a finite number; the line state combines the reading's own server
// label, its age on the device clock and the source state (worst wins).
export function readingLine(
  key: string,
  label: string,
  reading: unknown,
  source: SourceState,
  now: number,
  bounds: AgeBounds,
  format: ReadingFormat,
): ReadingLine {
  const missing: ReadingLine = { key, label, text: NO_DATA, state: "missing", note: null };
  if (!isObject(reading) || typeof reading.value !== "number" || !Number.isFinite(reading.value)) {
    return missing;
  }
  const eff = worstFreshness(
    reading.freshness,
    ageFreshness(reading.observed_at, now, bounds),
    source.state ?? "FRESH",
  );
  if (eff === "UNAVAILABLE") return missing;
  const age = ageLabel(reading.observed_at, now);
  const note = [eff === "FRESH" ? null : FRESHNESS_LABEL[eff], age].filter(Boolean).join(" · ");
  return {
    key,
    label,
    text: format(reading.value, reading.unit),
    state: eff === "FRESH" ? "ok" : eff === "RECENT" ? "recent" : "stale",
    note: note || null,
  };
}

export type ReadingsView = {
  // unavailable = source never succeeded / nothing to show; lines are empty then.
  unavailable: boolean;
  // Source-level warning (source not refreshing), null when healthy or unknown.
  sourceNote: string | null;
  lines: ReadingLine[];
  attribution: string | null;
};

export function sourceNote(source: SourceState, now: number): string | null {
  if (source.state !== "RECENT" && source.state !== "STALE") return null;
  const age = ageLabel(source.lastSuccessAt, now);
  const head = source.state === "STALE" ? "Źródło nie odświeża się" : "Źródło odświeża się z opóźnieniem";
  return age ? `${head} — ostatnia aktualizacja ${age}.` : `${head}.`;
}

// Shared by air and weather: builds the view from a block + the line specs.
export function buildView(
  block: unknown,
  specs: { key: string; label: string; format: ReadingFormat }[],
  bounds: AgeBounds,
  now: number,
): ReadingsView | null {
  if (!isObject(block)) return null;
  const params = isObject(block.params) ? block.params : {};
  const source = sourceState(block, now, bounds);
  const attribution = typeof block.attribution === "string" ? block.attribution : null;
  if (source.state === "UNAVAILABLE") {
    return { unavailable: true, sourceNote: null, lines: [], attribution };
  }
  const lines = specs.map((s) =>
    readingLine(s.key, s.label, params[s.key], source, now, bounds, s.format),
  );
  return { unavailable: false, sourceNote: sourceNote(source, now), lines, attribution };
}

// Air: every param the backend sent (PM2.5, PM10, NO2, ... - open set), same decimals
// as the raw GIOŚ values (up to 2, trailing zeros dropped).
export function airView(block: unknown, now: number): ReadingsView | null {
  if (!isObject(block)) return null;
  const params = isObject(block.params) ? block.params : {};
  const specs = Object.keys(params).map((code) => ({
    key: code,
    label: code,
    format: (v: number, unit: unknown) => withUnit(formatNumber(v, 2) ?? NO_DATA, unit),
  }));
  return buildView(block, specs, AIR_AGE, now);
}
