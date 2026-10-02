import { describe, expect, it } from "vitest";

import { type ForecastDay, forecastDayLabel, forecastLine, todayRange } from "./forecast";

const day = (params: Record<string, { value: number; unit: string }>) => ({
  valid_from: "2026-09-30T00:00:00+00:00", // a Wednesday
  valid_until: "2026-10-01T00:00:00+00:00",
  params,
});

describe("forecastDayLabel", () => {
  it("formats weekday with rounded max/min", () => {
    const label = forecastDayLabel(
      day({
        temperature_2m_max: { value: 18.5, unit: "°C" },
        temperature_2m_min: { value: 9.2, unit: "°C" },
      }),
    );
    expect(label).toMatch(/^śr\.? 19°\/9°$/);
  });

  it("returns null when max or min is missing instead of inventing a value", () => {
    expect(forecastDayLabel(day({ temperature_2m_max: { value: 18, unit: "°C" } }))).toBeNull();
  });
});

describe("forecastLine", () => {
  it("is null when no day has both max and min", () => {
    expect(forecastLine([day({ temperature_2m_max: { value: 18, unit: "°C" } })])).toBeNull();
  });

  it("limits to the first 3 days", () => {
    const d = day({
      temperature_2m_max: { value: 18, unit: "°C" },
      temperature_2m_min: { value: 9, unit: "°C" },
    });
    expect(forecastLine([d, d, d, d])?.split("   ")).toHaveLength(3);
  });

  it("skips incomplete days before applying the limit", () => {
    const full = day({
      temperature_2m_max: { value: 18, unit: "°C" },
      temperature_2m_min: { value: 9, unit: "°C" },
    });
    const partial = day({ temperature_2m_max: { value: 18, unit: "°C" } });
    expect(forecastLine([partial, full, full, full])?.split("   ")).toHaveLength(3);
  });
});

describe("todayRange", () => {
  const now = Date.parse("2026-10-02T12:00:00Z");
  const day = (over: Partial<ForecastDay> = {}): ForecastDay => ({
    valid_from: "2026-10-02T00:00:00Z",
    valid_until: "2026-10-03T00:00:00Z",
    params: { temperature_2m_max: { value: 18.4, unit: "°C" }, temperature_2m_min: { value: 8.6, unit: "°C" } },
    ...over,
  });
  const fc = (over = {}) => ({ days: [day()], fetched_at: "2026-10-02T11:00:00Z", freshness: "FRESH", ...over });
  const src = { freshness: "FRESH", last_success_at: "2026-10-02T11:00:00Z" };

  it("formats max/min of the running day", () => {
    expect(todayRange(fc(), src, now)).toBe("Dziś maks. 18° / min. 9°");
  });
  it("accepts RECENT, rejects STALE/UNAVAILABLE", () => {
    expect(todayRange(fc({ freshness: "RECENT" }), src, now)).not.toBeNull();
    expect(todayRange(fc({ freshness: "STALE" }), src, now)).toBeNull();
    expect(todayRange(fc(), { freshness: "UNAVAILABLE", last_success_at: null }, now)).toBeNull();
  });
  it("ages on the device clock even when the server label says FRESH", () => {
    expect(todayRange(fc({ fetched_at: "2026-10-02T00:30:00Z" }), src, now)).toBeNull();
  });
  it("is null when days[0] is not the running day or values are missing", () => {
    expect(todayRange(fc({ days: [day({ valid_from: "2026-10-01T00:00:00Z", valid_until: "2026-10-02T00:00:00Z" })] }), src, now)).toBeNull();
    expect(todayRange(fc({ days: [day({ params: {} })] }), src, now)).toBeNull();
    expect(todayRange(fc({ days: [] }), src, now)).toBeNull();
    expect(todayRange(null, src, now)).toBeNull();
  });
  it("older backend without source status adds no constraint", () => {
    expect(todayRange(fc(), null, now)).not.toBeNull();
  });
});
