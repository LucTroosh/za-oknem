// TASK-12.12: pure view models for the Air (S5) and Weather (S6) detail screens. Everything
// comes from the backend blocks the dashboard already carries; nothing is classified or
// estimated here (rule #10) and every gap is said out loud, never filled (rule #8).
import { type AirIndexView, AQI_LABEL, airIndexView, validAqiLevel } from "./aqi";
import { airCoverage, showAirIndex } from "./coverage";
import type { ForecastDay } from "./forecast";
import { type AgeBounds, FRESHNESS_LABEL, type FreshnessState, ageLabel, asFreshness } from "./freshness";
import { formatNumber, sourceState, withUnit } from "./readings";
import { weatherCodeText } from "./weather";

const isObject = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null && !Array.isArray(x);

// ---- air: station -----------------------------------------------------------------------

export type AirStationView = {
  name: string;
  distance: string | null; // "3,2 km"
  method: string | null; // how the station was assigned (ADR-025); unknown values are not guessed
  coverage: string; // wording of the band, honest about "here" vs "nearby" vs "area"
};

const METHOD_TEXT: Record<string, string> = { nearest_station: "najbliższa stacja pomiarowa" };

const COVERAGE_TEXT: Record<string, string> = {
  exact: "Stacja w Twojej miejscowości lub tuż przy niej (do 10 km).",
  nearby: "Stacja w pobliżu (do 50 km), nie w Twojej miejscowości.",
  regional: "Stacja w okolicy (50–100 km): stan dla obszaru, nie pomiar tutaj.",
};

// null = no station block (nothing within range): the screen says so, no empty rows.
export function airStation(air: unknown, coverage: unknown): AirStationView | null {
  if (!isObject(air)) return null;
  const name = typeof air.station_name === "string" && air.station_name.trim() !== "" ? air.station_name : null;
  if (name === null) return null;
  const d = typeof air.distance_km === "number" && Number.isFinite(air.distance_km) ? air.distance_km : null;
  const band = airCoverage(coverage, air).band;
  return {
    name,
    distance: d === null ? null : `${String(Math.round(d * 10) / 10).replace(".", ",")} km`,
    method: typeof air.assignment_method === "string" ? (METHOD_TEXT[air.assignment_method] ?? null) : null,
    coverage: band ? (COVERAGE_TEXT[band] ?? "") : "",
  };
}

// ---- air: index components ----------------------------------------------------------------

export type AirIndexDetail = {
  summary: AirIndexView;
  components: { param: string; label: string }[];
  dominant: string[]; // components that decide the level
  gaps: string[]; // "NO2: brak"
  complete: boolean;
  validUntil: string | null;
};

const GAP_TEXT: Record<string, string> = { MISSING: "brak", STALE: "nieaktualne", UNIT: "inna jednostka", INVALID: "błędne" };

// null whenever the index must not be shown: regional/none coverage, a silent/stale source
// (`suppressDerived`) or no usable block. `reason` for the screen is produced by airIndexUnavailable.
export function airIndexDetail(
  air: unknown,
  coverage: unknown,
  suppressDerived: boolean,
  now: number,
  receivedAt: number,
): AirIndexDetail | null {
  if (!isObject(air) || suppressDerived || !showAirIndex(coverage, air)) return null;
  const summary = airIndexView(air.index, now, receivedAt);
  if (!summary || summary.level === null) return null;
  const idx = air.index as Record<string, unknown>;
  const params = isObject(idx.params) ? idx.params : {};
  const components = Object.entries(params).flatMap(([param, level]) => {
    const l = validAqiLevel(level);
    return l ? [{ param, label: AQI_LABEL[l] }] : [];
  });
  const missing = isObject(idx.missing) ? idx.missing : {};
  return {
    summary,
    components,
    dominant: Array.isArray(idx.dominant) ? idx.dominant.filter((x): x is string => typeof x === "string") : [],
    gaps: Object.entries(missing).map(([p, s]) => `${p}: ${GAP_TEXT[String(s)] ?? "brak"}`),
    complete: idx.complete === true,
    validUntil: typeof idx.valid_until === "string" ? idx.valid_until : null,
  };
}

export function airIndexUnavailableText(air: unknown, coverage: unknown, suppressDerived: boolean): string {
  const cov = airCoverage(coverage, air);
  if (cov.unavailable) return "Brak indeksu: w okolicy nie ma stacji pomiarowej.";
  if (cov.band === "regional") return "Brak indeksu: najbliższa stacja jest za daleko, by mówić o Twojej miejscowości.";
  if (suppressDerived) return "Brak indeksu: źródło nie odświeża się, więc ocena mogłaby być nieaktualna.";
  return "Brak indeksu dla tej stacji (za mało świeżych pomiarów).";
}

// ---- source line ------------------------------------------------------------------------

export type SourceLine = { state: FreshnessState; text: string };

// "Status źródła: świeże, ostatnia udana aktualizacja 12 min temu". Ages on the device clock,
// worst of the server label and the age (via sourceState); unknown source -> null (no claim).
export function sourceLine(status: unknown, now: number, bounds: AgeBounds): SourceLine | null {
  if (!isObject(status)) return null;
  const s = sourceState({ source_status: status }, now, bounds);
  if (s.state === null) return null;
  const state = asFreshness(s.state);
  const when = ageLabel(s.lastSuccessAt, now);
  return {
    state,
    text:
      state === "UNAVAILABLE"
        ? "Status źródła: niedostępne, brak udanej aktualizacji."
        : `Status źródła: ${FRESHNESS_LABEL[state as keyof typeof FRESHNESS_LABEL]}${when ? `, ostatnia udana aktualizacja ${when}` : ""}.`,
  };
}

// ---- weather: daily forecast ---------------------------------------------------------------

export type ForecastRow = { key: string; day: string; range: string | null; precipitation: string | null; condition: string | null };

function param(day: ForecastDay, key: string): { value: number; unit: string } | null {
  const p = day.params?.[key];
  return p && typeof p.value === "number" && Number.isFinite(p.value) ? p : null;
}

// Days are UTC calendar days (Open-Meteo is queried with timezone=UTC, see forecast.ts), so
// the label carries the date. A day with neither range, precipitation nor condition is dropped.
export function forecastRows(days: ForecastDay[] | undefined, limit = 7): ForecastRow[] {
  return (days ?? [])
    .map((d) => {
      const max = param(d, "temperature_2m_max");
      const min = param(d, "temperature_2m_min");
      const rain = param(d, "precipitation_sum");
      const code = param(d, "weather_code");
      const label = new Date(d.valid_from).toLocaleDateString("pl-PL", { weekday: "long", day: "numeric", month: "numeric", timeZone: "UTC" });
      return {
        key: d.valid_from,
        day: label.charAt(0).toUpperCase() + label.slice(1),
        range: max && min ? `maks. ${Math.round(max.value)}° / min. ${Math.round(min.value)}°` : null,
        precipitation: rain ? `opady ${withUnit(formatNumber(rain.value, 1) ?? "?", rain.unit)}` : null,
        condition: code ? weatherCodeText(code.value) : null,
      };
    })
    .filter((r) => r.range !== null || r.precipitation !== null || r.condition !== null)
    .slice(0, limit);
}
