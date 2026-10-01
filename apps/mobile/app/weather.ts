// TASK-5.4: presentation of the dashboard `weather.params` fields. ONLY the params the
// backend really stores (connectors/open_meteo: CURRENT_PARAMS + HOURLY_PARAMS), with
// the unit the server sent - no conversions "by eye" except metres -> km for display.
// Missing = "brak danych", never 0; staleness handling lives in readings.ts (TASK-7.3).
import {
  NO_DATA,
  type ReadingFormat,
  type ReadingsView,
  WEATHER_AGE,
  buildView,
  formatNumber,
  withUnit,
} from "./readings";

const num =
  (decimals: number): ReadingFormat =>
  (v, unit) =>
    withUnit(formatNumber(v, decimals) ?? NO_DATA, unit);

// WMO weather interpretation codes (Open-Meteo `weather_code`, WMO 4677 subset).
const WMO: Record<number, string> = {
  0: "bezchmurnie",
  1: "przeważnie bezchmurnie",
  2: "częściowe zachmurzenie",
  3: "pochmurno",
  45: "mgła",
  48: "mgła osadzająca szron",
  51: "mżawka słaba",
  53: "mżawka umiarkowana",
  55: "mżawka gęsta",
  56: "marznąca mżawka słaba",
  57: "marznąca mżawka gęsta",
  61: "deszcz słaby",
  63: "deszcz umiarkowany",
  65: "deszcz silny",
  66: "marznący deszcz słaby",
  67: "marznący deszcz silny",
  71: "śnieg słaby",
  73: "śnieg umiarkowany",
  75: "śnieg silny",
  77: "ziarna śniegu",
  80: "przelotny deszcz słaby",
  81: "przelotny deszcz umiarkowany",
  82: "przelotny deszcz gwałtowny",
  85: "przelotny śnieg słaby",
  86: "przelotny śnieg silny",
  95: "burza",
  96: "burza z lekkim gradem",
  99: "burza z silnym gradem",
};

export function weatherCodeText(v: number): string {
  return WMO[v] ?? `kod pogody ${v}`;
}

const COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];

// 0-360 degrees the wind blows FROM -> "W (270°)". Outside the range = no data, not a guess.
export function windDirectionText(deg: number): string {
  if (deg < 0 || deg > 360) return NO_DATA;
  return `${COMPASS[Math.round(deg / 45) % 8]} (${Math.round(deg) % 360}°)`;
}

// Open-Meteo visibility is metres; show km from 1 km up, otherwise as sent.
export function visibilityText(v: number, unit: unknown): string {
  if (unit === "m" && v >= 1000) return `${formatNumber(v / 1000, 1)} km`;
  return withUnit(formatNumber(v, 0) ?? NO_DATA, unit);
}

// Stored param_code -> label. All of these exist in the backend; order = display order.
const SPECS = [
  { key: "temperature_2m", label: "Temperatura", format: num(1) },
  { key: "apparent_temperature", label: "Odczuwalna", format: num(1) },
  { key: "weather_code", label: "Stan", format: (v: number) => weatherCodeText(v) },
  { key: "wind_speed_10m", label: "Wiatr", format: num(0) },
  { key: "wind_gusts_10m", label: "Porywy", format: num(0) },
  { key: "wind_direction_10m", label: "Kierunek wiatru", format: (v: number) => windDirectionText(v) },
  { key: "precipitation", label: "Opady", format: num(1) },
  { key: "relative_humidity_2m", label: "Wilgotność", format: num(0) },
  { key: "pressure_msl", label: "Ciśnienie", format: num(0) },
  { key: "cloud_cover", label: "Zachmurzenie", format: num(0) },
  { key: "uv_index", label: "Indeks UV", format: num(1) },
  { key: "visibility", label: "Widzialność", format: visibilityText },
  { key: "dew_point_2m", label: "Punkt rosy", format: num(1) },
];

export function weatherView(block: unknown, now: number): ReadingsView | null {
  return buildView(block, SPECS, WEATHER_AGE, now);
}
