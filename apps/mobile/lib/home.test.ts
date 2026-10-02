import { describe, expect, it } from "vitest";

import {
  GLYPH_CHAR,
  STALE_NOTE,
  UNAVAILABLE_HEADLINE,
  pollingOff,
  pollingPending,
  selectArea,
  currentTemperature,
  formatHeaderDate,
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
    expect(verdictModel(outdoor("GOOD"), NOW, NOW)).toMatchObject({ level: "GOOD", headline: "Dziś warto wyjść na zewnątrz" });
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
  it("UNKNOWN is human copy first; the technical gap list is only a secondary detail", () => {
    const m = verdictModel({ level: "UNKNOWN", reasons: [], missing: [{ group: "air", params: [], status: "MISSING", blocking: true }] }, NOW, NOW);
    expect(m?.headline).toBe("Nie możemy jeszcze ocenić wszystkich warunków");
    expect(m?.supporting).toBe("Brakuje części aktualnych danych. Dostępne informacje pokazujemy poniżej.");
    for (const text of [m?.headline, m?.supporting]) expect(text).not.toMatch(/brak danych|\(brak\)|NO₂|O₃/i);
    expect(m?.details.join(" ")).toContain("jakość powietrza");
    expect(m?.reasons).toEqual([]);
  });
  it("a verdict computed without part of the data says so in human words", () => {
    const m = verdictModel({ level: "GOOD", reasons: [], missing: [{ group: "uv", params: ["uv_index"], status: "MISSING", blocking: false }], valid_until: new Date(NOW + 3600_000).toISOString() }, NOW, NOW);
    expect(m?.supporting).toContain("chwilowo niedostępna");
    expect(m?.details.length).toBe(1);
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

describe("formatHeaderDate", () => {
  it("Polish weekday and month, capitalised", () => {
    expect(formatHeaderDate(new Date(2026, 9, 1, 12).getTime())).toBe("Czwartek, 1 października");
  });
});

describe("selectArea", () => {
  it("picks the chosen area by id, never the first one", () => {
    expect(selectArea([{ geo_area_id: 5 }, { geo_area_id: 2 }], 5)).toEqual({ geo_area_id: 5 });
    expect(selectArea([{ geo_area_id: 5 }], 2)).toBeNull();
    expect(selectArea([], 2)).toBeNull();
  });
});

describe("pollingPending", () => {
  it("polling on but no first weather yet = data on its way, not unavailable", () => {
    expect(pollingPending({ weather_polling_active: true, weather: null, forecast: null })).toBe(true);
    expect(pollingPending({ weather_polling_active: true, weather: {}, forecast: null })).toBe(false);
    expect(pollingPending({ weather_polling_active: false, weather: null, forecast: null })).toBe(false);
    expect(pollingPending(null)).toBe(false);
  });
});

describe("pollingOff", () => {
  it("is true only for an explicit false (older backends omit the field)", () => {
    expect(pollingOff({ weather_polling_active: false })).toBe(true);
    expect(pollingOff({ weather_polling_active: true })).toBe(false);
    expect(pollingOff({})).toBe(false);
    expect(pollingOff(null)).toBe(false);
  });
});

describe("air card coverage (ADR-029)", () => {
  const withAir = (coverage: unknown, extra: Record<string, unknown> = {}) =>
    statusCards({ air: { ...air(), station_name: "Gliwice, ul. Mewy", distance_km: 3, ...extra }, weather: null, coverage }, null, NOW, NOW)[0];
  it("exact: no note", () => {
    expect(withAir({ air: "exact", air_radius_km: 10 }).coverageNote).toBeNull();
  });
  it("nearby: station and distance", () => {
    const c = withAir({ air: "nearby", air_radius_km: 50 }, { distance_km: 23.4 });
    expect(c.coverageNote).toBe("Dane ze stacji Gliwice, ul. Mewy, 23,4 km stąd.");
    expect(c.state).toBe("ready");
  });
  it("regional: explicit area state", () => {
    expect(withAir({ air: "regional", air_radius_km: 100 }, { distance_km: 71 }).coverageNote).toBe(
      "Stan dla obszaru w promieniu ok. 100 km — stacja Gliwice, ul. Mewy, 71 km.",
    );
  });
  it("regional is orientation: neutral level, the station as headline, never \"Dobra\" / green", () => {
    const c = withAir({ air: "regional", air_radius_km: 100 }, { distance_km: 71 });
    expect(c.level).toBe("UNKNOWN");
    expect(c.headline).toBe("Stacja Gliwice, ul. Mewy, 71 km");
    expect(c.supporting).toBe("Orientacyjnie, PM2.5: 12 µg/m³");
    expect(c.headline).not.toMatch(/Dobra|Co najmniej/);
  });
  it("weather and pollen cards say model, not measurement", () => {
    const cards = statusCards({ air: air(), weather: weather(), pollen: pollen({ alder: 0, birch: 1, grass: 1, mugwort: 0, ragweed: 0 }) }, null, NOW, NOW);
    expect(cards[1].coverageNote).toContain("nie pomiar");
    expect(cards[2].coverageNote).toContain("nie pomiar");
  });
  it("none: unavailable, never good, even if a block is present", () => {
    const c = withAir({ air: "none", air_radius_km: null });
    expect(c).toMatchObject({ state: "unavailable", level: "UNKNOWN", headline: "Brak stacji pomiarowej w okolicy", supporting: null });
    const noBlock = statusCards({ air: null, weather: null, coverage: { air: "none" } }, null, NOW, NOW)[0];
    expect(noBlock.headline).toBe("Brak stacji pomiarowej w okolicy");
  });
});
