// TASK-5.5: compact daily forecast line ("śr 18°/9°"). Values come straight from
// the server (dashboard.py forecast block) - nothing is estimated here.
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
