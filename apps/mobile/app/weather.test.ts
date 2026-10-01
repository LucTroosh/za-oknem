import { describe, expect, it } from "vitest";

import { visibilityText, weatherCodeText, weatherView, windDirectionText } from "./weather";

const NOW = Date.parse("2026-10-01T12:00:00Z");
const ago = (min: number) => new Date(NOW - min * 60_000).toISOString();
const p = (value: unknown, unit: string, min = 10, freshness = "FRESH") => ({
  value,
  unit,
  observed_at: ago(min),
  freshness,
});

const block = (params: Record<string, unknown>, extra: object = {}) => ({
  attribution: "Open-Meteo",
  params,
  source_status: { freshness: "FRESH", last_success_at: ago(10) },
  ...extra,
});

const line = (v: ReturnType<typeof weatherView>, key: string) => v?.lines.find((l) => l.key === key);

describe("weatherView fields and units", () => {
  const params = {
    temperature_2m: p(-3.44, "°C"),
    apparent_temperature: p(-7, "°C"),
    weather_code: p(61, "wmo code"),
    wind_speed_10m: p(12.4, "km/h"),
    wind_gusts_10m: p(25.6, "km/h"),
    wind_direction_10m: p(270, "°"),
    precipitation: p(0, "mm"),
    relative_humidity_2m: p(55, "%"),
    pressure_msl: p(1013.2, "hPa"),
    cloud_cover: p(100, "%"),
    uv_index: p(0, ""),
    visibility: p(24140, "m"),
    dew_point_2m: p(-5.5, "°C"),
  };
  it("renders each stored field with its unit, in display order", () => {
    const v = weatherView(block(params), NOW);
    expect(v?.lines.map((l) => l.text)).toEqual([
      "-3,4 °C",
      "-7 °C",
      "deszcz słaby",
      "12 km/h",
      "26 km/h",
      "W (270°)",
      "0 mm",
      "55%",
      "1013 hPa",
      "100%",
      "0",
      "24,1 km",
      "-5,5 °C",
    ]);
    expect(v?.lines.every((l) => l.state === "ok")).toBe(true);
  });
  it("zero precipitation and UV 0 are values, not 'brak'", () => {
    const v = weatherView(block(params), NOW);
    expect(line(v, "precipitation")?.state).toBe("ok");
    expect(line(v, "uv_index")?.text).toBe("0");
  });
  it("params the backend did not send, or sent as null, read 'brak danych'", () => {
    const v = weatherView(block({ temperature_2m: p(null, "°C"), uv_index: p(1, "") }), NOW);
    expect(line(v, "temperature_2m")).toMatchObject({ text: "brak danych", state: "missing" });
    expect(line(v, "wind_speed_10m")).toMatchObject({ text: "brak danych", state: "missing" });
    expect(line(v, "uv_index")?.text).toBe("1");
  });
});

describe("weatherView staleness", () => {
  it("one stale hourly-derived param does not taint fresh current ones", () => {
    const v = weatherView(
      block({ temperature_2m: p(10, "°C"), uv_index: p(3, "", 900, "STALE") }),
      NOW,
    );
    expect(line(v, "temperature_2m")?.state).toBe("ok");
    expect(line(v, "uv_index")).toMatchObject({ state: "stale", note: "nieaktualne · 15 godz. temu" });
  });
  it("source_status STALE dims everything and warns, even with FRESH row labels", () => {
    const v = weatherView(
      block({ temperature_2m: p(10, "°C") }, { source_status: { freshness: "STALE", last_success_at: ago(600) } }),
      NOW,
    );
    expect(line(v, "temperature_2m")?.state).toBe("stale");
    expect(v?.sourceNote).toContain("ostatnia aktualizacja 10 godz. temu");
  });
  it("source_status UNAVAILABLE hides values", () => {
    const v = weatherView(
      block({ temperature_2m: p(10, "°C") }, { source_status: { freshness: "UNAVAILABLE", last_success_at: null } }),
      NOW,
    );
    expect(v).toMatchObject({ unavailable: true, lines: [] });
  });
  it("weather bounds are 4h/8h (not the air 2h/6h)", () => {
    const v = weatherView(block({ temperature_2m: p(10, "°C", 200) }), NOW);
    expect(line(v, "temperature_2m")?.state).toBe("ok");
  });
  it("no block -> null", () => {
    expect(weatherView(null, NOW)).toBeNull();
  });
});

describe("helpers", () => {
  it("weatherCodeText: known, zero and unknown codes", () => {
    expect(weatherCodeText(0)).toBe("bezchmurnie");
    expect(weatherCodeText(95)).toBe("burza");
    expect(weatherCodeText(42)).toBe("kod pogody 42");
  });
  it("windDirectionText: compass + degrees, 360 wraps, out of range is no data", () => {
    expect(windDirectionText(0)).toBe("N (0°)");
    expect(windDirectionText(360)).toBe("N (0°)");
    expect(windDirectionText(350)).toBe("N (350°)");
    expect(windDirectionText(45)).toBe("NE (45°)");
    expect(windDirectionText(-1)).toBe("brak danych");
    expect(windDirectionText(400)).toBe("brak danych");
  });
  it("visibilityText: km from 1000 m, metres below, foreign unit untouched", () => {
    expect(visibilityText(24140, "m")).toBe("24,1 km");
    expect(visibilityText(800, "m")).toBe("800 m");
    expect(visibilityText(0, "m")).toBe("0 m");
    expect(visibilityText(5, "km")).toBe("5 km");
  });
});
