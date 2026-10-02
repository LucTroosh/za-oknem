// Structure of the Start screen (spec §4, §9-§17, §40-§44, §50): pure logic only - wording,
// glyph levels, which modules exist and in what order. Components just lay it out.
// Nothing here classifies a measurement (rule #10): levels come from the backend blocks
// (outdoor verdict, EAQI, pollen thresholds); this maps them to copy and decides what a
// card may CLAIM when data is old or missing (rule #8, ADR-012).
import { type AirIndexView, airIndexView } from "./aqi";
import { MODEL_NOTE, NO_STATION_HEADLINE, airCoverage } from "./coverage";
import { type OutdoorLevel, outdoorView } from "./outdoor";
import { POLLEN_NAME, type PollenLevel, pollenView } from "./pollen";
import { type LineState, type ReadingLine, type ReadingsView, airView, formatNumber } from "./readings";
import { weatherCodeText, weatherView } from "./weather";

// Spec §15. Never colour alone: every level has a glyph and a word.
export type GlyphLevel = "GOOD" | "CAUTION" | "AVOID" | "UNKNOWN";

export const GLYPH_WORD: Record<GlyphLevel, string> = {
  GOOD: "Dobre warunki",
  CAUTION: "Zachowaj ostrożność",
  AVOID: "Lepiej odpuścić",
  UNKNOWN: "Brak wystarczających danych",
};

// Verbatim spec glyphs; the screen draws them with the one icon library (components/StatusGlyph).
export const GLYPH_CHAR: Record<GlyphLevel, string> = { GOOD: "✓", CAUTION: "!", AVOID: "×", UNKNOWN: "?" };

const OUTDOOR_LEVEL: Record<OutdoorLevel, GlyphLevel> = {
  GOOD: "GOOD",
  MODERATE: "CAUTION",
  POOR: "AVOID",
  UNKNOWN: "UNKNOWN",
};

// Production UI v1 §7/§14: answer-first, human copy. The verdict itself (level, reasons, gaps) is
// the backend's (rule #10); this only words it. Internal diagnostics ("brak danych: ... (brak)")
// never reach the headline: they live in `details`, behind a disclosure.
export const VERDICT_HEADLINE: Record<GlyphLevel, string> = {
  GOOD: "Dziś warto wyjść na zewnątrz",
  CAUTION: "Warunki są dziś średnie",
  AVOID: "Lepiej ograniczyć aktywność na zewnątrz",
  UNKNOWN: "Nie możemy jeszcze ocenić wszystkich warunków",
};

export const VERDICT_SUPPORTING: Record<GlyphLevel, string> = {
  GOOD: "Według dostępnych danych nic nie stoi na przeszkodzie.",
  CAUTION: "Część wskaźników przekracza progi. Powody poniżej.",
  AVOID: "Część wskaźników przekracza progi. Powody poniżej.",
  UNKNOWN: "Brakuje części aktualnych danych. Dostępne informacje pokazujemy poniżej.",
};

export const VERDICT_PARTIAL_NOTE = "Część danych jest chwilowo niedostępna, więc nie została uwzględniona.";

export type VerdictModel = {
  level: GlyphLevel;
  headline: string;
  // One short human sentence under the headline (never a variable name or a source name).
  supporting: string;
  // Backend reasons, already formatted by outdoorView (no invented advice). Shown on tap.
  reasons: string[];
  // Technical gaps ("Brak oceny - brak danych: ..."): secondary disclosure only.
  details: string[];
};

// null = the backend sent no verdict block (older backend): the hero disappears, never a mock.
export function verdictModel(outdoor: unknown, now: number, receivedAt: number): VerdictModel | null {
  const v = outdoorView(outdoor, now, receivedAt);
  if (!v) return null;
  const level = OUTDOOR_LEVEL[v.level];
  const unknown = v.level === "UNKNOWN";
  const partial = !unknown && v.missingLine !== null;
  return {
    level,
    headline: VERDICT_HEADLINE[level],
    supporting: partial ? `${VERDICT_SUPPORTING[level]} ${VERDICT_PARTIAL_NOTE}` : VERDICT_SUPPORTING[level],
    reasons: unknown ? [] : v.reasonLines,
    details: unknown ? [v.headline] : v.missingLine ? [v.missingLine] : [],
  };
}

// ---- header -------------------------------------------------------------------------------

// "Czwartek, 1 października" (device clock, Polish).
export function formatHeaderDate(now: number): string {
  const s = new Date(now).toLocaleDateString("pl-PL", { weekday: "long", day: "numeric", month: "long" });
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// ---- status cards -------------------------------------------------------------------------

export type ModuleKey = "air" | "weather" | "pollen";

export type StatusCardModel = {
  key: ModuleKey;
  title: string;
  // unavailable = nothing trustworthy to show; the card says so instead of vanishing (§42).
  state: "ready" | "unavailable";
  // null = information without a good/bad reading (weather): no status glyph.
  level: GlyphLevel | null;
  headline: string;
  supporting: string | null;
  // "Dane z 17:00" / "Dane mogą być nieaktualne" (§43), null when fresh.
  freshnessNote: string | null;
  // Air only: where the measurement comes from when it is not "right here" (lib/coverage.ts).
  coverageNote: string | null;
};

export const UNAVAILABLE_HEADLINE = "Dane chwilowo niedostępne";
export const STALE_NOTE = "Dane mogą być nieaktualne";

function unavailable(key: ModuleKey, title: string, headline = UNAVAILABLE_HEADLINE): StatusCardModel {
  return { key, title, state: "unavailable", level: "UNKNOWN", headline, supporting: null, freshnessNote: null, coverageNote: null };
}

const isObject = (x: unknown): x is Record<string, unknown> =>
  typeof x === "object" && x !== null && !Array.isArray(x);

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

// Same day -> "Dane z 17:00"; another day -> with the date (STALE is only a coarse age bucket,
// so a bare "17:00" could be yesterday).
export function dataFrom(iso: unknown, now: number): string | null {
  const t = typeof iso === "string" ? new Date(iso) : null;
  if (!t || Number.isNaN(t.getTime())) return null;
  const hm = `${pad(t.getHours())}:${pad(t.getMinutes())}`;
  const n = new Date(now);
  const same = t.getFullYear() === n.getFullYear() && t.getMonth() === n.getMonth() && t.getDate() === n.getDate();
  return `Dane z ${same ? "" : `${pad(t.getDate())}.${pad(t.getMonth() + 1)}, `}${hm}`;
}

// Note for a value of state `state` observed at `iso`: fresh -> none, recent -> "Dane z HH:MM",
// stale -> "Dane mogą być nieaktualne" (+ when it is from).
function freshnessNote(state: LineState | "ok", iso: unknown, now: number): string | null {
  if (state === "ok" || state === "missing") return null;
  const from = dataFrom(iso, now);
  if (state === "recent") return from ?? STALE_NOTE;
  return from ? `${STALE_NOTE} (${from.toLowerCase()})` : STALE_NOTE;
}

function paramIso(block: unknown, key: string): unknown {
  const params = isObject(block) && isObject(block.params) ? block.params : {};
  const p = params[key];
  return isObject(p) ? p.observed_at : undefined;
}

const STATE_RANK: Record<LineState, number> = { ok: 0, missing: 0, recent: 1, stale: 2 };

// The card's freshness is that of its WORST usable input (an index depends on several
// pollutants, not just PM2.5); ties: the oldest observation.
function worstLine(block: unknown, lines: ReadingLine[]): ReadingLine | undefined {
  const at = (l: ReadingLine) => {
    const t = Date.parse(String(paramIso(block, l.key)));
    return Number.isNaN(t) ? 0 : t;
  };
  return lines
    .filter((l) => l.state !== "missing")
    .reduce<ReadingLine | undefined>(
      (a, l) => (!a || STATE_RANK[l.state] > STATE_RANK[a.state] || (STATE_RANK[l.state] === STATE_RANK[a.state] && at(l) < at(a)) ? l : a),
      undefined,
    );
}

const AQI_GLYPH: Record<string, GlyphLevel> = { GOOD: "GOOD", FAIR: "GOOD", MODERATE: "CAUTION" };

function airCard(air: unknown, coverage: unknown, sourceStatus: unknown, now: number, receivedAt: number): StatusCardModel {
  const title = "Powietrze";
  // No station within 100 km: UNAVAILABLE, whatever else the block holds - never "good".
  const cov = airCoverage(coverage, air);
  if (cov.unavailable) return unavailable("air", title, NO_STATION_HEADLINE);
  const view: ReadingsView | null = airView(air, now, sourceStatus);
  if (view === null) return unavailable("air", title, "Brak stacji w pobliżu");
  if (view.unavailable) return unavailable("air", title);
  const pm = view.lines.find((l) => /^PM2[.,]?5$/i.test(l.key));
  const pmUsable = pm !== undefined && pm.state !== "missing";
  // A silent/old source must not keep a derived verdict (same rule as the details).
  if (view.suppressDerived) {
    return {
      key: "air",
      title,
      state: "ready",
      level: "UNKNOWN",
      headline: "Brak aktualnej oceny",
      supporting: pmUsable ? `PM2.5: ${pm.text}` : null,
      freshnessNote: STALE_NOTE,
      coverageNote: cov.note,
    };
  }
  // Regional (50-100 km): orientation only. Neutral level, the station as the headline - never
  // "Dobra" and no green glyph (the verdict engine ignores it too, ADR-029).
  if (cov.band === "regional") {
    return {
      key: "air",
      title,
      state: "ready",
      level: "UNKNOWN",
      headline: cov.headline ?? "Stacja w okolicy",
      supporting: pmUsable ? `Orientacyjnie, PM2.5: ${pm.text}` : null,
      freshnessNote: ((w) => (w ? freshnessNote(w.state, paramIso(air, w.key), now) : null))(worstLine(air, view.lines)),
      coverageNote: cov.note,
    };
  }
  const index: AirIndexView | null = airIndexView(isObject(air) ? air.index : undefined, now, receivedAt);
  const level = index?.level ? (AQI_GLYPH[index.level] ?? "AVOID") : "UNKNOWN";
  return {
    key: "air",
    title,
    state: "ready",
    level,
    // An incomplete pollutant set is only a lower bound (airIndexView's own wording).
    headline: index?.level
      ? isObject(air) && isObject(air.index) && air.index.complete === true
        ? index.label
        : `Co najmniej ${index.label.toLowerCase()}`
      : "Brak oceny",
    supporting: pmUsable ? `PM2.5: ${pm.text}` : null,
    freshnessNote: ((w) => (w ? freshnessNote(w.state, paramIso(air, w.key), now) : null))(worstLine(air, view.lines)),
    coverageNote: cov.note,
  };
}

function celsius(v: number, unit: unknown): string {
  const n = formatNumber(v, 0) ?? "?";
  return unit === "°C" || unit === undefined ? `${n}°C` : `${n} ${String(unit)}`;
}

function weatherReading(weather: unknown, key: string): { value: number; unit: unknown } | null {
  const params = isObject(weather) && isObject(weather.params) ? weather.params : {};
  const p = params[key];
  return isObject(p) && typeof p.value === "number" && Number.isFinite(p.value)
    ? { value: p.value, unit: p.unit }
    : null;
}

// Temperature shown in the header / card: only when its reading is usable and not stale.
// `onlyFresh` (header): a RECENT reading can be hours old and the header carries no age note,
// so it shows FRESH readings only; the weather card shows RECENT ones with "Dane z HH:MM".
export function currentTemperature(
  weather: unknown,
  sourceStatus: unknown,
  now: number,
  onlyFresh = false,
): string | null {
  const view = weatherView(weather, now, sourceStatus);
  const line = view?.lines.find((l) => l.key === "temperature_2m");
  const r = weatherReading(weather, "temperature_2m");
  if (!view || view.unavailable || !line || line.state === "missing" || line.state === "stale" || (onlyFresh && line.state !== "ok") || !r) {
    return null;
  }
  return celsius(r.value, r.unit);
}

function weatherCard(weather: unknown, sourceStatus: unknown, now: number): StatusCardModel {
  const title = "Pogoda";
  const view = weatherView(weather, now, sourceStatus);
  if (view === null) return unavailable("weather", title, "Brak danych pogodowych");
  if (view.unavailable) return unavailable("weather", title);
  const tempLine = view.lines.find((l) => l.key === "temperature_2m");
  const codeLine = view.lines.find((l) => l.key === "weather_code");
  const usable = (l: typeof tempLine) => l !== undefined && l.state !== "missing";
  if (!usable(tempLine) && !usable(codeLine)) return unavailable("weather", title);
  const temp = tempLine && tempLine.state !== "stale" ? currentTemperature(weather, sourceStatus, now) : null;
  const code = weatherReading(weather, "weather_code");
  const condition = usable(codeLine) && codeLine?.state !== "stale" && code ? weatherCodeText(code.value) : null;
  // An old temperature is never the headline of a "current weather" card.
  if (temp === null && condition === null) {
    return { ...unavailable("weather", title, STALE_NOTE), freshnessNote: null };
  }
  // Only the parts actually shown count (a stale temperature that is hidden is not the note).
  const shown = [temp !== null ? tempLine : undefined, condition !== null ? codeLine : undefined].filter(
    (l): l is ReadingLine => l !== undefined,
  );
  const worst = worstLine(weather, shown);
  return {
    key: "weather",
    title,
    state: "ready",
    level: null,
    headline: temp ?? (condition as string),
    supporting: temp !== null ? condition : null,
    freshnessNote: worst ? freshnessNote(worst.state, paramIso(weather, worst.key), now) : null,
    coverageNote: MODEL_NOTE,
  };
}

const POLLEN_RANK: Record<PollenLevel, number> = { BELOW_SEASON: 0, SEASON: 1, PEAK: 2 };
const POLLEN_GLYPH: Record<PollenLevel, GlyphLevel> = { BELOW_SEASON: "GOOD", SEASON: "CAUTION", PEAK: "AVOID" };
const POLLEN_HEADLINE: Record<PollenLevel, string> = {
  BELOW_SEASON: "Niskie",
  SEASON: "Sezon pylenia",
  PEAK: "Szczyt pylenia",
};
// The values are a CAMS model forecast, never a trap measurement (rule #7).
export const POLLEN_CARD_TITLE = "Prognoza pyłków";
export const POLLEN_FORECAST_NOTE = "Prognoza modelu CAMS";

function pollenCard(pollen: unknown, now: number): StatusCardModel | null {
  const view = pollenView(pollen);
  if (!view) return null;
  const title = POLLEN_CARD_TITLE;
  if (view.state === "unavailable") return unavailable("pollen", title);
  if (view.state === "stale") return unavailable("pollen", title, STALE_NOTE);
  const levels = view.lines.filter((l): l is typeof l & { level: PollenLevel } => l.level !== null);
  if (levels.length === 0) return unavailable("pollen", title);
  const top = levels.reduce((a, l) => (POLLEN_RANK[l.level] > POLLEN_RANK[a] ? l.level : a), levels[0].level);
  const driving = levels.filter((l) => l.level === top && top !== "BELOW_SEASON").map((l) => POLLEN_NAME[l.species]);
  // A species without a value could be higher: all-below-season with gaps is not "Niskie".
  const missing = view.lines.filter((l) => l.level === null).map((l) => POLLEN_NAME[l.species]);
  // Any gap below a known PEAK: the missing species could be higher, so the aggregate is a lower bound.
  const partial = missing.length > 0 && top !== "PEAK";
  const parts = [
    driving.length > 0 ? `${partial ? "Co najmniej: " : ""}${POLLEN_HEADLINE[top].toLowerCase()} (${driving.join(", ")})` : null,
    missing.length > 0 ? `Brak danych: ${missing.join(", ")}` : null,
    POLLEN_FORECAST_NOTE,
  ].filter(Boolean);
  return {
    key: "pollen",
    title,
    state: "ready",
    level: partial ? "UNKNOWN" : POLLEN_GLYPH[top],
    headline: partial ? "Dane częściowe" : POLLEN_HEADLINE[top],
    supporting: `${parts.join(". ")}`,
    freshnessNote: view.state === "recent" ? (dataFrom(view.fetchedAt, now) ?? STALE_NOTE) : null,
    coverageNote: MODEL_NOTE,
  };
}

export type AreaLike = { air?: unknown; weather?: unknown; pollen?: unknown; coverage?: unknown };

// Data-driven list (§50): air and weather are core modules and always get a card (a failed
// one says "niedostępne"); pollen only when the backend sent the block; a future module
// (water) is simply added here once it has a source - the layout takes any length.
export function statusCards(
  area: AreaLike,
  sourceStatus: { air?: unknown; weather?: unknown } | null,
  now: number,
  receivedAt: number,
): StatusCardModel[] {
  const pollen = pollenCard(area.pollen, now);
  return [
    airCard(area.air, area.coverage, sourceStatus?.air, now, receivedAt),
    weatherCard(area.weather, sourceStatus?.weather, now),
    ...(pollen ? [pollen] : []),
  ];
}

// The dashboard is requested with ?geo_area_id=, so it holds exactly the chosen area; still
// pick it by id - never "the first one" (the order of the response is not part of the contract).
export function selectArea<T extends { geo_area_id: number }>(areas: T[], geoAreaId: number): T | null {
  return areas.find((a) => a.geo_area_id === geoAreaId) ?? null;
}

// `weather_polling_active === false`: nobody collects weather for this place right now
// (capacity, budget or expired activation). Strictly false - an older backend without the
// field must not trigger it.
// Freshly activated place: polling is on but the first fetch has not landed yet (ADR-029:
// minutes). Not "unavailable" - the data is on its way.
export function pollingPending(area: { weather_polling_active?: boolean; weather?: unknown; forecast?: unknown } | null): boolean {
  return area !== null && area.weather_polling_active === true && !area.weather && !area.forecast;
}

export function pollingOff(area: { weather_polling_active?: boolean } | null): boolean {
  return area !== null && area.weather_polling_active === false;
}
