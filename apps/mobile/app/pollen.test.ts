import { describe, expect, it } from "vitest";

import {
  POLLEN_SPECIES,
  type PollenBlock,
  effectiveFreshness,
  formatPollenValue,
  pollenLevel,
  pollenView,
} from "./pollen";

const ALL_NULL = { alder: null, birch: null, grass: null, mugwort: null, ragweed: null };

const block = (over: Partial<PollenBlock> = {}): PollenBlock => ({
  source: "open_meteo_pollen",
  attribution: "Pollen forecast: CAMS via Open-Meteo.com",
  kind: "model_forecast",
  model: "cams_europe",
  unit: "grains/m³",
  forecast_reference_time: "2026-10-01T00:00:00Z",
  fetched_at: "2026-10-01T06:00:00Z",
  freshness: "FRESH",
  valid_at: "2026-10-01T12:00:00Z",
  current: { ...ALL_NULL, birch: 12.5, grass: 2, alder: 0, mugwort: 100, ragweed: 50 },
  days: [],
  source_status: { freshness: "FRESH", last_success_at: "2026-10-01T06:00:00Z" },
  ...over,
});

describe("pollenLevel (EAACI season/peak thresholds via CAMS/EEA)", () => {
  it("uses 10/100 for alder, birch, mugwort and 3/50 for grass, ragweed", () => {
    expect(pollenLevel("birch", 9.9, "grains/m³")).toBe("BELOW_SEASON");
    expect(pollenLevel("birch", 10, "grains/m³")).toBe("SEASON");
    expect(pollenLevel("birch", 100, "grains/m³")).toBe("PEAK");
    expect(pollenLevel("grass", 2.9, "grains/m³")).toBe("BELOW_SEASON");
    expect(pollenLevel("grass", 3, "grains/m³")).toBe("SEASON");
    expect(pollenLevel("ragweed", 50, "grains/m³")).toBe("PEAK");
  });
  it("gives no level for null, negative, NaN or a foreign unit (no conversion)", () => {
    expect(pollenLevel("birch", null, "grains/m³")).toBeNull();
    expect(pollenLevel("birch", -1, "grains/m³")).toBeNull();
    expect(pollenLevel("birch", Number.NaN, "grains/m³")).toBeNull();
    expect(pollenLevel("birch", 500, "pollen/m³")).toBeNull();
  });
});

describe("pollenView", () => {
  it("is null for a missing/garbage block or without attribution", () => {
    expect(pollenView(undefined)).toBeNull();
    expect(pollenView(null)).toBeNull();
    expect(pollenView([1])).toBeNull();
    expect(pollenView(block({ attribution: "" }))).toBeNull();
  });

  it("labels the data as a CAMS model forecast, not a measurement", () => {
    const v = pollenView(block());
    expect(v?.title).toBe("Pyłki — prognoza modelu CAMS (nie pomiar)");
    expect(v?.attribution).toBe("Pollen forecast: CAMS via Open-Meteo.com");
    expect(v?.state).toBe("ok");
    expect(v?.status).toBeNull();
  });

  it("shows all five species in order with levels, a modelled 0 as 0 and null as brak danych", () => {
    const v = pollenView(block());
    expect(v?.lines.map((l) => l.species)).toEqual(POLLEN_SPECIES);
    expect(v?.lines.map((l) => l.text)).toEqual([
      "poniżej progu sezonu (0 grains/m³)", // alder 0 stays 0
      "sezon pylenia (13 grains/m³)",
      "poniżej progu sezonu (2 grains/m³)",
      "szczyt pylenia (100 grains/m³)",
      "szczyt pylenia (50 grains/m³)",
    ]);
    const missing = pollenView(block({ current: { ...ALL_NULL, birch: 1 } }));
    expect(missing?.lines.map((l) => l.text)[0]).toBe("brak danych");
    expect(missing?.lines.map((l) => l.level)[0]).toBeNull();
  });

  it("shows the raw value with its unit and no level when the unit is not grains/m³", () => {
    const v = pollenView(block({ unit: "pollen/m³" }));
    expect(v?.lines[1].text).toBe("13 pollen/m³");
    expect(v?.lines[1].level).toBeNull();
  });

  it("flags RECENT data but still shows it", () => {
    const v = pollenView(block({ freshness: "RECENT" }));
    expect(v?.state).toBe("recent");
    expect(v?.lines.length).toBe(5);
    expect(v?.status).toBe("Dane niedawne — prognoza mogła się już zmienić.");
  });

  it("STALE shows no levels, only an explicit notice", () => {
    const v = pollenView(block({ freshness: "STALE" }));
    expect(v?.state).toBe("stale");
    expect(v?.lines).toEqual([]);
    expect(v?.status).toBe("Dane o pyłkach są nieaktualne — nie pokazujemy poziomów.");
  });

  it("UNAVAILABLE (no snapshot) says brak danych", () => {
    const v = pollenView(
      block({ freshness: "UNAVAILABLE", current: null, fetched_at: null, unit: null }),
    );
    expect(v?.state).toBe("unavailable");
    expect(v?.lines).toEqual([]);
    expect(v?.status).toBe("Brak danych o pyłkach.");
  });

  it("a fresh area whose run no longer covers the current hour (current null) is unavailable", () => {
    expect(pollenView(block({ current: null }))?.state).toBe("unavailable");
  });

  it("a stale source overrides a fresh area (worse of the two wins)", () => {
    const stale = pollenView(
      block({ source_status: { freshness: "STALE", last_success_at: "2026-09-25T00:00:00Z" } }),
    );
    expect(stale?.state).toBe("stale");
    const down = pollenView(
      block({ source_status: { freshness: "UNAVAILABLE", last_success_at: null } }),
    );
    expect(down?.state).toBe("unavailable");
  });
});

describe("effectiveFreshness / formatPollenValue", () => {
  it("treats unknown values as UNAVAILABLE", () => {
    expect(effectiveFreshness({ freshness: "WAT", source_status: {} })).toBe("UNAVAILABLE");
    expect(effectiveFreshness({ freshness: "FRESH" })).toBe("UNAVAILABLE");
    expect(effectiveFreshness({ freshness: "FRESH", source_status: { freshness: "RECENT" } })).toBe(
      "RECENT",
    );
  });
  it("formats with a Polish decimal comma and rounds large values", () => {
    expect(formatPollenValue(0)).toBe("0");
    expect(formatPollenValue(2.34)).toBe("2,3");
    expect(formatPollenValue(123.6)).toBe("124");
  });
});
