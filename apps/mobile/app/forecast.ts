// TASK-5.5: compact daily forecast line ("śr 18°/9°"). Values come straight from
// the server (dashboard.py forecast block) - nothing is estimated here.
export type ForecastDay = {
  valid_from: string;
  valid_until: string;
  params: Record<string, { value: number; unit: string }>;
};

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
  const labels = days
    .slice(0, limit)
    .map((day) => forecastDayLabel(day))
    .filter((label): label is string => label !== null);
  return labels.length > 0 ? labels.join("   ") : null;
}
