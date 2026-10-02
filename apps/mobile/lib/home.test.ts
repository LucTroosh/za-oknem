import { describe, expect, it } from "vitest";

import {
  ALERTS_NONE_TEXT,
  GLYPH_CHAR,
  STALE_NOTE,
  UNAVAILABLE_HEADLINE,
  alertsStatus,
  currentTemperature,
  formatHeaderDate,
  sectionOrder,
  statusCards,
  verdictModel,
} from "./home";

const NOW = Date.parse("2026-10-01T12:00:00Z");
const ago = (min: number) => new Date(NOW - min * 60_000).toISOString();
const param = (value: unknown, unit: string, min = 10, freshness = "FRESH") => ({
  value,
  unit,
  observed_at: ago(min),
  freshness,
});
const src = { freshness: "FRESH", last_success_at: ago(10) };

const air = (pm = param(12, "µg/m³"), level: string | null = "GOOD") => ({
  attribution: "GIOŚ",
  params: { "PM2.5": pm },
  source_status: src,
  index: { level, complete: true, params: {}, missing: {}, dominant: [] },
});
const weather = (extra: Record<string, unknown> = {}) => ({
  attribution: "Open-Meteo",
  params: { temperature_2m: param(16.4, "°C"), weather_code: param(0, "wmo code"), ...extra },
  source_status: src,
});
const pollen = (current: Record<string, number>, freshness = "FRESH") => ({
  attribution: "CAMS",
  freshness,
  source_status: { freshness: freshness === "UNAVAILABLE" ? "UNAVAILABLE" : "FRESH", last_success_at: ago(30) },
  unit: "grains/m³",
  fetched_at: ago(30),
  valid_at: ago(0),
  current,
});

describe("verdictModel", () => {
  const outdoor = (level: string) => ({ level, reasons: [], missing: [], valid_until: new Date(NOW + 3600_000).toISOString() });
  it("maps backend levels to spec glyph levels and Polish headlines", () => {
    expect(verdictModel(outdoor("GOOD"), NOW, NOW)).toMatchObject({ level: "GOOD", headline: "Dobre warunki na zewnątrz" });
    expect(verdictModel(outdoor("MODERATE"), NOW, NOW)?.level).toBe("CAUTION");
    expect(verdictModel(outdoor("POOR"), NOW, NOW)?.level).toBe("AVOID");
    expect(verdictModel(outdoor("UNKNOWN"), NOW, NOW)?.level).toBe("UNKNOWN");
  });
  it("an expired verdict stops asserting itself", () => {
    expect(verdictModel(outdoor("GOOD"), NOW + 2 * 3600_000, NOW)?.level).toBe("UNKNOWN");
  });
  it("no block = no hero (never a mock)", () => {
    expect(verdictModel(undefined, NOW, NOW)).toBeNull();
  });
  it("glyphs are the spec's", () => {
    expect(GLYPH_CHAR).toEqual({ GOOD: "✓", CAUTION: "!", AVOID: "×", UNKNOWN: "?" });
  });
});

describe("statusCards (data-driven, partial failure)", () => {
  it("renders air, weather and pollen when all present, in that order", () => {
    const cards = statusCards({ air: air(), weather: weather(), pollen: pollen({ alder: 0, birch: 1, grass: 1, mugwort: 0, ragweed: 0 }) }, null, NOW, NOW);
    expect(cards.map((c) => c.key)).toEqual(["air", "weather", "pollen"]);
    expect(cards[0]).toMatchObject({ level: "GOOD", headline: "Dobra", supporting: "PM2.5: 12 µg/m³", freshnessNote: null });
    expect(cards[1]).toMatchObject({ headline: "16°C", supporting: "bezchmurnie", level: null });
    expect(cards[2]).toMatchObject({ title: "Prognoza pyłków", headline: "Niskie", level: "GOOD" });
    expect(cards[2].supporting).toContain("CAMS");
  });
  it("omits pollen when the backend sent none; air/weather stay as 'niedostępne'", () => {
    const cards = statusCards({ air: null, weather: null }, { air: { freshness: "UNAVAILABLE", last_success_at: null } }, NOW, NOW);
    expect(cards.map((c) => c.key)).toEqual(["air", "weather"]);
    expect(cards[0]).toMatchObject({ state: "unavailable", headline: UNAVAILABLE_HEADLINE });
  });
  it("one failed module does not touch the others", () => {
    const cards = statusCards({ air: air(), weather: weather(), pollen: pollen({}, "UNAVAILABLE") }, null, NOW, NOW);
    expect(cards[2]).toMatchObject({ state: "unavailable", headline: UNAVAILABLE_HEADLINE });
    expect(cards[0].state).toBe("ready");
  });
  it("pollen level is the worst species and names it; thresholds from lib/pollen", () => {
    const [, , c] = statusCards({ air: null, weather: null, pollen: pollen({ birch: 120, grass: 5 }) }, null, NOW, NOW);
    expect(c).toMatchObject({ headline: "Szczyt pylenia", level: "AVOID" });
    expect(c.supporting).toContain("Brzoza");
    expect(c.supporting?.includes("Trawy")).toBe(false);
  });
  it("recent data carries 'Dane z HH:MM'; stale data says it may be outdated", () => {
    const recent = statusCards({ air: air(param(12, "µg/m³", 180, "RECENT")), weather: weather() }, null, NOW, NOW)[0];
    expect(recent.freshnessNote).toMatch(/^Dane z \d\d:\d\d$/);
    const stale = statusCards({ air: air(param(12, "µg/m³", 600, "STALE")), weather: weather() }, null, NOW, NOW)[0];
    expect(stale.freshnessNote).toContain(STALE_NOTE);
  });
  it("air freshness is the worst of ALL inputs, not only PM2.5", () => {
    const a = air();
    (a.params as Record<string, unknown>).NO2 = param(20, "µg/m³", 180, "RECENT");
    expect(statusCards({ air: a, weather: null }, null, NOW, NOW)[0].freshnessNote).toMatch(/^Dane z \d\d:\d\d$/);
    (a.params as Record<string, unknown>).O3 = param(50, "µg/m³", 600, "STALE");
    expect(statusCards({ air: a, weather: null }, null, NOW, NOW)[0].freshnessNote).toContain(STALE_NOTE);
  });
  it("weather note follows the shown parts (recent condition, fresh temperature)", () => {
    const w = weather({ weather_code: param(0, "wmo code", 180, "RECENT") });
    expect(statusCards({ air: null, weather: w }, null, NOW, NOW)[1].freshnessNote).toMatch(/^Dane z /);
  });
  it("an old temperature is not the headline of the current-weather card", () => {
    const w = weather({ temperature_2m: param(16, "°C", 9 * 60, "STALE"), weather_code: param(0, "wmo code", 9 * 60, "STALE") });
    const c = statusCards({ air: null, weather: w }, null, NOW, NOW)[1];
    expect(c.state).toBe("unavailable");
    expect(currentTemperature(w, undefined, NOW)).toBeNull();
  });
  it("partial pollen data is not 'Niskie'; the header shows fresh temperatures only", () => {
    const [, , c] = statusCards({ air: null, weather: null, pollen: pollen({ birch: 1, grass: null as unknown as number }) }, null, NOW, NOW);
    expect(c).toMatchObject({ headline: "Dane częściowe", level: "UNKNOWN" });
    expect(c.supporting).toContain("Brak danych");
    const w = weather({ temperature_2m: param(16, "°C", 180, "RECENT") });
    expect(currentTemperature(w, undefined, NOW)).toBe("16°C");
    expect(currentTemperature(w, undefined, NOW, true)).toBeNull();
  });
  it("SEASON with a missing species is still partial (could be PEAK); PEAK stays definitive", () => {
    const season = pollen({ alder: 0, birch: 20, grass: null as unknown as number, mugwort: 0, ragweed: 0 });
    const [, , c] = statusCards({ air: null, weather: null, pollen: season }, null, NOW, NOW);
    expect(c).toMatchObject({ headline: "Dane częściowe", level: "UNKNOWN" });
    expect(c.supporting).toContain("Co najmniej");
    const peak = pollen({ alder: 0, birch: 200, grass: null as unknown as number, mugwort: 0, ragweed: 0 });
    expect(statusCards({ air: null, weather: null, pollen: peak }, null, NOW, NOW)[2]).toMatchObject({ headline: "Szczyt pylenia" });
  });
  it("an incomplete AQI set reads 'Co najmniej …'", () => {
    const a = air();
    (a.index as { complete: boolean }).complete = false;
    expect(statusCards({ air: a, weather: null }, null, NOW, NOW)[0].headline).toBe("Co najmniej dobra");
  });
  it("pollen recent note compares with the screen clock (another day shows the date)", () => {
    const p = { ...pollen({ birch: 1 }, "RECENT"), source_status: src, fetched_at: ago(40 * 60), current: { alder: 0, birch: 1, grass: 1, mugwort: 0, ragweed: 0 } };
    const [, , c] = statusCards({ air: null, weather: null, pollen: p }, null, NOW, NOW);
    expect(c.freshnessNote).toMatch(/^Dane z \d\d\.\d\d, \d\d:\d\d$/);
  });
  it("currentTemperature rounds and keeps the spec format", () => {
    expect(currentTemperature(weather(), undefined, NOW)).toBe("16°C");
  });
});

describe("alertsStatus (empty != unavailable, §44)", () => {
  const warn = { tone: "warning", text: "w" } as const;
  const neutral = { tone: "neutral", text: "n" } as const;
  const loaded = { alerts: true, hydro: true };
  it("confirmed all-clear", () => {
    expect(alertsStatus([null, null], loaded)).toEqual({ kind: "none" });
    expect(ALERTS_NONE_TEXT).toBe("Brak aktywnych ostrzeżeń");
  });
  it("could-not-check is a different state", () => {
    expect(alertsStatus([neutral, null], loaded).kind).toBe("unavailable");
  });
  it("still loading is neither", () => {
    expect(alertsStatus([null, null], { alerts: true, hydro: false })).toEqual({ kind: "loading" });
  });
  it("a real warning wins even while the other source loads", () => {
    expect(alertsStatus([warn, null], { alerts: true, hydro: false }).kind).toBe("active");
  });
});

describe("sectionOrder", () => {
  it("header, verdict, cards, alerts, calendar by default", () => {
    expect(sectionOrder({ kind: "none" })).toEqual(["header", "verdict", "cards", "alerts", "calendar"]);
    expect(sectionOrder({ kind: "unavailable", banners: [] })).toEqual(["header", "verdict", "cards", "alerts", "calendar"]);
  });
  it("a significant alert moves up under the header", () => {
    expect(sectionOrder({ kind: "active", banners: [] })).toEqual(["header", "alerts", "verdict", "cards", "calendar"]);
  });
});

describe("formatHeaderDate", () => {
  it("Polish weekday and month, capitalised", () => {
    expect(formatHeaderDate(new Date(2026, 9, 1, 12).getTime())).toBe("Czwartek, 1 października");
  });
});
