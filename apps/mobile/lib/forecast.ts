// TASK-5.5: compact daily forecast line ("śr 18°/9°"). Values come straight from
// the server (dashboard.py forecast block) - nothing is estimated here.
import { ageFreshness, worstFreshness } from "./freshness";
import { WEATHER_AGE } from "./readings";
import type {
  DashboardForecastDay,
  DashboardForecastHour,
} from "../../../packages/api-contract/schema";

export type ForecastDay = DashboardForecastDay;
// ADR-030: next up to 48 h, a separate list from `days`; no UI yet (TASK-7.9 / window).
export type ForecastHour = DashboardForecastHour;

// ponytail: days are UTC calendar days (Open-Meteo is queried with timezone=UTC,
// client.py), so near midnight the label can be off by one vs. Polish local time.
// Switch the request to timezone=Europe/Warsaw if that ever matters to users.
export function forecastDayLabel(day: ForecastDay): string | null {
  const max = day.params.temperature_2m_max;
  const min = day.params.temperature_2m_min;
  if (!max || !min) return null;
  const weekday = new Date(day.valid_from).toLocaleDateString("pl-PL", {
    weekday: "short",
    timeZone: "UTC",
  });
  return `${weekday} ${Math.round(max.value)}°/${Math.round(min.value)}°`;
}

// Up to `limit` days joined into one line; null when no day has both max and min,
// so the screen shows nothing rather than an empty "Prognoza:" label.
export function forecastLine(days: ForecastDay[], limit = 3): string | null {
  // Filter BEFORE limiting (Codex): an incomplete day must not use up one of the
  // `limit` slots and hide a later complete day.
  const labels = days
    .map((day) => forecastDayLabel(day))
    .filter((label): label is string => label !== null)
    .slice(0, limit);
  return labels.length > 0 ? labels.join("   ") : null;
}

// Header line under the date: today's max/min from `forecast.days[0]` (spec §10). Only when
// that day is the one running NOW (valid_from <= now < valid_until: days are UTC calendar
// days, see above) and the forecast is usable: the worst of its own label, its age on the
// device clock and the weather source status must be FRESH/RECENT (ADR-012). Otherwise null:
// the header shows nothing rather than an old or foreign day's numbers.
export type ForecastLike = {
  days?: ForecastDay[];
  fetched_at?: string;
  freshness?: unknown;
} | null;

export function todayRange(forecast: ForecastLike, weatherSource: unknown, now: number): string | null {
  const day = forecast?.days?.[0];
  if (!forecast || !day) return null;
  const from = Date.parse(day.valid_from);
  const until = Date.parse(day.valid_until);
  if (!Number.isFinite(from) || !Number.isFinite(until) || now < from || now >= until) return null;
  const src = typeof weatherSource === "object" && weatherSource !== null ? (weatherSource as Record<string, unknown>) : null;
  const state = worstFreshness(
    forecast.freshness,
    ageFreshness(forecast.fetched_at, now, WEATHER_AGE),
    src ? src.freshness : "FRESH",
    src ? ageFreshness(src.last_success_at, now, WEATHER_AGE) : "FRESH",
  );
  if (state !== "FRESH" && state !== "RECENT") return null;
  const max = day.params.temperature_2m_max;
  const min = day.params.temperature_2m_min;
  if (!max || !min || !Number.isFinite(max.value) || !Number.isFinite(min.value)) return null;
  return `Dziś maks. ${Math.round(max.value)}° / min. ${Math.round(min.value)}°`;
}
