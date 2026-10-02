// WMO weather_code (Open-Meteo) -> one Ionicons glyph (production UI v1 §1, one icon library).
// A glyph never replaces the condition text next to it; unknown codes get no icon at all.
export type WeatherIcon = "sunny" | "partly-sunny" | "cloudy" | "rainy" | "thunderstorm" | "snow" | "cloud-outline";

export function weatherIcon(code: number): WeatherIcon | null {
  if (!Number.isFinite(code)) return null;
  if (code === 0 || code === 1) return "sunny";
  if (code === 2) return "partly-sunny";
  if (code === 3) return "cloudy";
  if (code === 45 || code === 48) return "cloud-outline"; // fog
  if ((code >= 51 && code <= 67) || (code >= 80 && code <= 82)) return "rainy";
  if ((code >= 71 && code <= 77) || code === 85 || code === 86) return "snow";
  if (code >= 95 && code <= 99) return "thunderstorm";
  return null;
}
