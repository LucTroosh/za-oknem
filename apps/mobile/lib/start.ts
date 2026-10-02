// Production UI v1: pure view models of the Start screen. Everything here is derived from data the
// app already has (statusCards, weather block, local alerts); no module is faked. A domain with no
// production source is simply absent (no empty tile), an unavailable one says so in words.
import { type AlertItem, type AlertsBlock } from "./alerts";
import { type AlertsScreenModel, buildAlertsScreen } from "./alertsScreen";
import { type StatusCardModel, currentTemperature, statusCards } from "./home";
import { formatNumber } from "./readings";
import type { Domain } from "./theme";
import { weatherView } from "./weather";
import { type WeatherIcon, weatherIcon } from "./weatherIcon";

export type TileKey = "air" | "weather" | "pollen" | "uv";
export type TileRoute = "/air" | "/weather" | "/pollen";

export type QuickTile = {
  key: TileKey;
  domain: Domain;
  icon: "leaf" | "partly-sunny" | "flower" | "sunny";
  label: string;
  value: string;
  supporting: string | null;
  unavailable: boolean;
  route: TileRoute;
};

const TITLE: Record<TileKey, string> = { air: "Powietrze", weather: "Pogoda", pollen: "Pyłki", uv: "UV" };
const ICON = { air: "leaf", weather: "partly-sunny", pollen: "flower", uv: "sunny" } as const;
const ROUTE: Record<TileKey, TileRoute> = { air: "/air", weather: "/weather", pollen: "/pollen", uv: "/weather" };
const DOMAIN: Record<TileKey, Domain> = { air: "air", weather: "weather", pollen: "pollen", uv: "uv" };

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function fromCard(c: StatusCardModel): QuickTile {
  const key = c.key;
  const base = { key, domain: DOMAIN[key], icon: ICON[key], label: TITLE[key], route: ROUTE[key] };
  // "unavailable" and "no assessment" never look like a good value: neutral tile, plain words.
  if (c.state === "unavailable" || c.level === "UNKNOWN") {
    const air = key === "air";
    return {
      ...base,
      value: c.state === "unavailable" ? "Niedostępne" : "Brak oceny",
      supporting: air && c.headline.startsWith("Brak stacji") ? "Brak stacji w okolicy" : c.state === "unavailable" ? c.headline.replace(/^Dane chwilowo niedostępne$/, "Dane chwilowo niedostępne") : (c.supporting ?? c.headline),
      unavailable: true,
    };
  }
  if (key === "air") {
    const atLeast = c.headline.startsWith("Co najmniej ");
    const value = cap(atLeast ? c.headline.slice("Co najmniej ".length) : c.headline);
    const pm = c.supporting ?? null;
    return { ...base, value, supporting: [atLeast ? "co najmniej" : null, pm].filter(Boolean).join(" · ") || null, unavailable: false };
  }
  if (key === "weather") {
    return { ...base, value: c.headline, supporting: c.supporting ? cap(c.supporting) : "Prognoza dla Twojego obszaru", unavailable: false };
  }
  // pollen: the headline is the model's level; the long species list lives on the pollen screen.
  return { ...base, value: c.headline, supporting: "Prognoza modelu", unavailable: false };
}

// UV only when the weather block has a usable, non-stale uv_index reading. Index number as sent by
// the model; no category words (that would be our own classification, rule #10).
export function uvTile(weather: unknown, weatherStatus: unknown, now: number): QuickTile | null {
  const view = weatherView(weather, now, weatherStatus);
  const line = view?.lines.find((l) => l.key === "uv_index");
  if (!view || view.unavailable || !line || line.state === "missing" || line.state === "stale") return null;
  const params = (weather as { params?: Record<string, { value?: unknown }> }).params;
  const raw = params?.uv_index?.value;
  const text = typeof raw === "number" ? formatNumber(raw, 1) : null;
  if (!text) return null;
  return { key: "uv", domain: "uv", icon: "sunny", label: TITLE.uv, value: text, supporting: "Indeks UV", unavailable: false, route: "/weather" };
}

export function quickTiles(
  area: { air?: unknown; weather?: unknown; pollen?: unknown; coverage?: unknown },
  sourceStatus: { air?: unknown; weather?: unknown } | null,
  now: number,
  receivedAt: number,
): QuickTile[] {
  const tiles = statusCards(area, sourceStatus, now, receivedAt).map(fromCard);
  const uv = uvTile(area.weather, sourceStatus?.weather, now);
  return uv ? [...tiles, uv] : tiles;
}

// Responsive grid (§5/§16): one row only while the tiles stay READABLE, otherwise 2 x 2. Readable
// means no word is cut in the middle: the longest word of any tile value / supporting line must fit
// the tile's inner width (approximate glyph widths at 1.0 font scale: ~8.4 dp per char in the 17 dp
// bold value, ~5.4 dp in the 11-12 dp supporting line). Big system font (>= 1.3) always goes to 2 columns.
export const TILE_MIN_WIDTH = 76;
const TILE_PADDING = 20; // 10 + 10
const VALUE_CHAR = 8.4;
const SUPPORT_CHAR = 5.4;

export function quickGridColumns(contentWidth: number, fontScale: number, count: number, longest = { value: 0, supporting: 0 }): number {
  if (count <= 0) return 1;
  if (count <= 2) return count;
  const tileWidth = (contentWidth - 8 * (count - 1)) / count;
  const inner = tileWidth - TILE_PADDING;
  const fits = longest.value * VALUE_CHAR <= inner && longest.supporting * SUPPORT_CHAR <= inner;
  const oneRow = contentWidth >= 328 && fontScale < 1.3 && tileWidth >= TILE_MIN_WIDTH && fits;
  return oneRow ? count : 2;
}

const longestWord = (text: string | null | undefined) => (text ?? "").split(/\s+/).reduce((m, w) => Math.max(m, w.length), 0);

// Longest word in the tiles' value and supporting lines (input of quickGridColumns).
export function longestTileWords(tiles: QuickTile[]): { value: number; supporting: number } {
  return {
    value: tiles.reduce((m, t) => Math.max(m, longestWord(t.value)), 0),
    supporting: tiles.reduce((m, t) => Math.max(m, longestWord(t.supporting)), 0),
  };
}

// ---- alert preview ---------------------------------------------------------------------------

export type AlertPreview =
  | { kind: "local"; tone: "danger" | "warning"; title: string; detail: string; count: number }
  | { kind: "unresolved"; title: string; detail: string; count: number }
  | { kind: "unknown"; title: string; detail: string }
  | { kind: "clear"; title: string };

// What Start may say about warnings, deliberately small (§7E): a relevant local warning, an
// uncertainty that matters (cannot check / cannot place), or a confirmed all-clear. Nationwide
// counts and unrelated hydrology never appear here. `null` = nothing to say yet (still loading).
export function alertPreview(
  block: AlertsBlock | null,
  localAlerts: AlertItem[] | null | undefined,
  now: number,
  refreshFailed: boolean,
  loading: boolean,
): AlertPreview | null {
  if (!block) {
    return loading ? null : { kind: "unknown", title: "Nie udało się sprawdzić ostrzeżeń", detail: "Nie potwierdzamy, że ich nie ma. Spróbuj odświeżyć." };
  }
  const m: AlertsScreenModel = buildAlertsScreen(block, localAlerts, now, refreshFailed);
  if (m.localStatus === "has-local") {
    const first = m.local[0];
    const n = m.local.length;
    return {
      kind: "local",
      tone: "danger",
      title: n === 1 ? (/^ostrze/i.test(first.event_type) ? first.event_type : `Ostrzeżenie: ${first.event_type}`) : `Ostrzeżenia w Twoim województwie: ${n}`,
      detail: n === 1 ? `Stopień ${first.severity_raw}. Źródło: IMGW.` : "Zobacz szczegóły i treść komunikatów.",
      count: n,
    };
  }
  if (m.unresolved.length > 0) {
    return {
      kind: "unresolved",
      title: "Część ostrzeżeń wymaga sprawdzenia",
      detail: "Nie da się ustalić, czy dotyczą Twojej lokalizacji.",
      count: m.unresolved.length,
    };
  }
  if (m.localStatus === "none-confirmed") return { kind: "clear", title: "Brak aktywnych ostrzeżeń" };
  return { kind: "unknown", title: "Nie udało się sprawdzić ostrzeżeń", detail: "Nie potwierdzamy, że ich nie ma." };
}

// Glyph for the header / weather hero: only from a usable (not stale) weather_code reading.
export function currentWeatherIcon(weather: unknown, weatherStatus: unknown, now: number): WeatherIcon | null {
  const view = weatherView(weather, now, weatherStatus);
  const line = view?.lines.find((l) => l.key === "weather_code");
  if (!view || view.unavailable || !line || line.state === "missing" || line.state === "stale") return null;
  const raw = (weather as { params?: Record<string, { value?: unknown }> }).params?.weather_code?.value;
  return typeof raw === "number" ? weatherIcon(raw) : null;
}

// ---- weather detail ----------------------------------------------------------------------------

export type WeatherHero = { temp: string | null; condition: string | null; icon: WeatherIcon | null; summary: string | null };

// Top of the weather screen: only usable (not stale) current values. `summary` is a factual one-liner
// built from the same readings (no advice, nothing invented); null when there is nothing to say.
export function weatherHero(weather: unknown, weatherStatus: unknown, now: number): WeatherHero {
  const view = weatherView(weather, now, weatherStatus);
  const usable = (key: string) => {
    const l = view?.lines.find((x) => x.key === key);
    return l && !view?.unavailable && l.state !== "missing" && l.state !== "stale" ? l : null;
  };
  const temp = currentTemperature(weather, weatherStatus, now);
  const code = usable("weather_code");
  const apparent = usable("apparent_temperature");
  const condition = code ? cap(code.text) : null;
  const parts = [condition, temp ? `${temp}` : null].filter(Boolean).join(", ");
  const summary = parts ? `${parts}.${apparent ? ` Odczuwalna ${apparent.text}.` : ""}` : null;
  return { temp, condition, icon: currentWeatherIcon(weather, weatherStatus, now), summary };
}

export type WeatherMetric = {
  key: string;
  icon: "rainy-outline" | "speedometer-outline" | "navigate-outline" | "water-outline" | "analytics-outline" | "cloudy-outline" | "sunny-outline" | "eye-outline" | "thermometer-outline";
  label: string;
  value: string;
  note: string | null;
  dim: boolean;
};

const METRIC_ICON: Record<string, WeatherMetric["icon"]> = {
  apparent_temperature: "thermometer-outline",
  precipitation: "rainy-outline",
  wind_speed_10m: "speedometer-outline",
  wind_gusts_10m: "speedometer-outline",
  wind_direction_10m: "navigate-outline",
  relative_humidity_2m: "water-outline",
  pressure_msl: "analytics-outline",
  cloud_cover: "cloudy-outline",
  uv_index: "sunny-outline",
  visibility: "eye-outline",
  dew_point_2m: "water-outline",
};

// The measurement grid: every reading the backend stores except the hero ones, only the ones that
// exist (a missing field is omitted, never 0), an old reading dimmed with its age.
export function weatherMetrics(weather: unknown, weatherStatus: unknown, now: number): WeatherMetric[] {
  const view = weatherView(weather, now, weatherStatus);
  if (!view || view.unavailable) return [];
  return view.lines
    .filter((l) => l.key !== "temperature_2m" && l.key !== "weather_code" && l.state !== "missing")
    .map((l) => ({
      key: l.key,
      icon: METRIC_ICON[l.key] ?? "analytics-outline",
      label: l.label,
      value: l.text,
      // Age only when it matters (recent / old); a fresh reading needs no "25 min temu" on every tile.
      note: l.state === "stale" ? "nieaktualne" : l.state === "recent" ? l.note : null,
      dim: l.state === "stale",
    }));
}
