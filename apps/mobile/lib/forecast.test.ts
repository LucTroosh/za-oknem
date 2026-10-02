import { describe, expect, it } from "vitest";

import { type ForecastDay, forecastDayLabel, forecastLine, hourlyStrip, todayRange } from "./forecast";

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

describe("hourlyStrip", () => {
  const now = Date.parse("2026-10-02T12:30:00Z");
  const hour = (iso: string, temp: number | null, code?: number) => ({
    valid_from: iso,
    valid_until: new Date(Date.parse(iso) + 3600_000).toISOString(),
    params: {
      ...(temp === null ? {} : { temperature_2m: { value: temp, unit: "°C" } }),
      ...(code === undefined ? {} : { weather_code: { value: code, unit: "" } }),
    },
  });
  const fc = (hours: ReturnType<typeof hour>[], over = {}) => ({ days: [], hours, fetched_at: "2026-10-02T11:00:00Z", freshness: "FRESH", ...over });
  const src = { freshness: "FRESH", last_success_at: "2026-10-02T11:00:00Z" };

  it("starts with the hour that contains now, skips the past and hours without a temperature", () => {
    const cells = hourlyStrip(
      fc([hour("2026-10-02T11:00:00Z", 10, 0), hour("2026-10-02T12:00:00Z", 11.6, 61), hour("2026-10-02T13:00:00Z", null), hour("2026-10-02T14:00:00Z", 13, 3)]),
      src,
      now,
    );
    expect(cells.map((c) => c.temp)).toEqual(["12°", "13°"]);
    expect(cells[0].icon).toBe("rainy");
    expect(cells[0].time).toMatch(/^\d\d:00$/);
  });
  it("respects the limit and never shows an old or silent forecast", () => {
    const hours = Array.from({ length: 20 }, (_, i) => hour(new Date(Date.parse("2026-10-02T12:00:00Z") + i * 3600_000).toISOString(), i));
    expect(hourlyStrip(fc(hours), src, now, 5)).toHaveLength(5);
    expect(hourlyStrip(fc(hours, { freshness: "STALE" }), src, now)).toEqual([]);
    expect(hourlyStrip(fc(hours), { freshness: "UNAVAILABLE", last_success_at: null }, now)).toEqual([]);
    expect(hourlyStrip(null, src, now)).toEqual([]);
  });
});
