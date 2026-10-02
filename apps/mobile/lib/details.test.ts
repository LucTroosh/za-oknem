import { describe, expect, it } from "vitest";

import { airHero, airIndexDetail, airIndexUnavailableText, airMeaning, airMetrics, airStation, forecastRows, sourceLine } from "./details";
import { AIR_AGE } from "./readings";

const NOW = Date.parse("2026-10-02T12:00:00Z");
const air = (over: Record<string, unknown> = {}) => ({
  station_name: "Gliwice, ul. Mewy",
  distance_km: 3.24,
  assignment_method: "nearest_station",
  coverage: "exact",
  index: {
    level: "MODERATE",
    complete: false,
    params: { PM10: "MODERATE", PM2_5: "GOOD", NO2: "FAIR" },
    missing: { O3: "STALE", SO2: "MISSING" },
    dominant: ["PM10"],
    valid_until: "2026-10-02T13:00:00Z",
  },
  ...over,
});

describe("airStation", () => {
  it("names the station, distance and band without claiming 'your town' for nearby", () => {
    const v = airStation(air({ coverage: "nearby" }), { air: "nearby" });
    expect(v?.name).toBe("Gliwice, ul. Mewy");
    expect(v?.distance).toBe("3,2 km");
    expect(v?.method).toBe("najbliższa stacja pomiarowa");
    expect(v?.coverage).toContain("nie w Twojej miejscowości");
  });
  it("does not guess an unknown assignment method; null without a station", () => {
    expect(airStation(air({ assignment_method: "magic" }), { air: "exact" })?.method).toBeNull();
    expect(airStation(null, { air: "none" })).toBeNull();
  });
});

describe("airIndexDetail", () => {
  const rt = NOW;
  it("lists components, dominant, gaps and the incomplete flag", () => {
    const d = airIndexDetail(air(), { air: "exact" }, false, NOW, rt);
    expect(d?.components).toEqual([
      { param: "PM10", label: "Umiarkowana" },
      { param: "PM2_5", label: "Dobra" },
      { param: "NO2", label: "Zadowalająca" },
    ]);
    expect(d?.gaps).toEqual(["O3: nieaktualne", "SO2: brak"]);
    expect(d?.dominant).toEqual(["PM10"]);
    expect(d?.complete).toBe(false);
    expect(d?.summary.headline).toContain("co najmniej");
  });
  it("no index for regional/none, silent source, expired or null level", () => {
    expect(airIndexDetail(air(), { air: "regional" }, false, NOW, rt)).toBeNull();
    expect(airIndexDetail(air(), { air: "none" }, false, NOW, rt)).toBeNull();
    expect(airIndexDetail(air(), { air: "exact" }, true, NOW, rt)).toBeNull();
    expect(airIndexDetail(air(), { air: "exact" }, false, NOW + 2 * 3600_000, rt)).toBeNull();
    expect(airIndexDetail(air({ index: { level: null, complete: false, params: {}, missing: {}, dominant: [] } }), { air: "exact" }, false, NOW, rt)).toBeNull();
  });
  it("explains why there is no index", () => {
    expect(airIndexUnavailableText(null, { air: "none" }, false)).toContain("nie ma stacji");
    expect(airIndexUnavailableText(air(), { air: "regional" }, false)).toContain("za daleko");
    expect(airIndexUnavailableText(air(), { air: "exact" }, true)).toContain("nie odświeża");
  });
});

describe("sourceLine", () => {
  it("combines the server label with the device clock age", () => {
    const fresh = { freshness: "FRESH", last_success_at: "2026-10-02T11:50:00Z" };
    expect(sourceLine(fresh, NOW, AIR_AGE)?.text).toBe("Status źródła: świeże, ostatnia udana aktualizacja 10 min temu.");
    const old = { freshness: "FRESH", last_success_at: "2026-10-02T01:00:00Z" };
    expect(sourceLine(old, NOW, AIR_AGE)?.state).toBe("STALE");
  });
  it("unavailable and unknown", () => {
    expect(sourceLine({ freshness: "UNAVAILABLE", last_success_at: null }, NOW, AIR_AGE)?.text).toContain("niedostępne");
    expect(sourceLine(undefined, NOW, AIR_AGE)).toBeNull();
  });
});

describe("forecastRows", () => {
  const day = (params: Record<string, { value: number; unit: string }>, from = "2026-10-02T00:00:00Z") => ({ valid_from: from, valid_until: "2026-10-03T00:00:00Z", params });
  it("formats range, precipitation and condition; drops empty days", () => {
    const rows = forecastRows([
      day({ temperature_2m_max: { value: 17.6, unit: "°C" }, temperature_2m_min: { value: 8.4, unit: "°C" }, precipitation_sum: { value: 2.5, unit: "mm" }, weather_code: { value: 61, unit: "" } }),
      day({}, "2026-10-03T00:00:00Z"),
    ]);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({ range: "maks. 18° / min. 8°", precipitation: "opady 2,5 mm", condition: "deszcz słaby" });
    expect(rows[0].day).toMatch(/^Piątek/);
  });
  it("undefined input", () => {
    expect(forecastRows(undefined)).toEqual([]);
  });
});

describe("air detail view models", () => {
  const rt = NOW;
  const pm = (v: number, min = 10) => ({ value: v, unit: "µg/m³", observed_at: new Date(NOW - min * 60_000).toISOString(), freshness: "FRESH" });
  const withParams = (extra: Record<string, unknown> = {}) => air({ params: { "PM2.5": pm(12.4), PM10: pm(28.1, 900), ...extra } });
  it("hero is human copy with the real 1..6 scale step", () => {
    const h = airHero(withParams(), { air: "exact" }, false, NOW, rt);
    expect(h).toMatchObject({ tone: "warning", step: 3 });
    expect(h.headline).toBe("Co najmniej umiarkowana jakość powietrza"); // fixture index is incomplete
  });
  it("no index -> neutral, no scale, plain reason (never a good-looking headline)", () => {
    const h = airHero(withParams(), { air: "regional" }, false, NOW, rt);
    expect(h).toMatchObject({ tone: "neutral", step: null, headline: "Nie możemy ocenić jakości powietrza" });
    expect(h.supporting).toMatch(/za daleko/);
  });
  it("meaning is factual lines (decisive component, gaps), no health advice", () => {
    const lines = airMeaning(airIndexDetail(withParams(), { air: "exact" }, false, NOW, rt));
    expect(lines[0]).toContain("GIOŚ");
    expect(lines.join(" ")).toContain("PM10");
    expect(lines.join(" ")).toContain("O3: nieaktualne");
    expect(airMeaning(null)).toEqual([]);
  });
  it("metrics: value, unit, age; an old one dimmed; empty for a silent block", () => {
    const m = airMetrics(withParams(), NOW, { freshness: "FRESH", last_success_at: new Date(NOW - 600_000).toISOString() });
    expect(m.find((x) => x.key === "PM2.5")).toMatchObject({ value: "12,4", dim: false });
    expect(m.find((x) => x.key === "PM2.5")?.note).toContain("µg/m³");
    expect(m.find((x) => x.key === "PM10")).toMatchObject({ dim: true });
    expect(airMetrics(null, NOW, null)).toEqual([]);
  });
});
