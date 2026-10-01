import { describe, expect, it } from "vitest";

import {
  AQI_FALLBACK_MAX_AGE_MS,
  AQI_LABEL,
  type AirIndexBlock,
  aqiGaps,
  aqiStep,
  airIndexView,
  validAqiLevel,
} from "./aqi";

const NOW = Date.parse("2026-09-30T12:00:00Z");
const LATER = "2026-09-30T14:00:00Z";

const block = (over: Partial<AirIndexBlock> = {}): AirIndexBlock => ({
  level: "GOOD",
  complete: true,
  params: { "PM2.5": "GOOD" },
  dominant: ["PM2.5"],
  missing: {},
  valid_until: LATER,
  ...over,
});

describe("labels and steps", () => {
  it("has a distinct Polish label for each of the six EEA bands, in order", () => {
    const levels = ["GOOD", "FAIR", "MODERATE", "POOR", "VERY_POOR", "EXTREMELY_POOR"] as const;
    expect(new Set(levels.map((l) => AQI_LABEL[l])).size).toBe(6);
    expect(levels.map(aqiStep)).toEqual([1, 2, 3, 4, 5, 6]);
  });

  it("rejects unknown levels", () => {
    expect(validAqiLevel("POOR")).toBe("POOR");
    expect(validAqiLevel("VERY_GOOD")).toBeNull();
    expect(validAqiLevel(null)).toBeNull();
    expect(validAqiLevel(3)).toBeNull();
  });
});

describe("aqiGaps", () => {
  it("names pollutant and reason", () => {
    expect(aqiGaps({ NO2: "MISSING", O3: "STALE", SO2: "UNIT" })).toBe(
      "NO2 (brak), O3 (nieaktualne), SO2 (inna jednostka)",
    );
  });
  it("tolerates garbage", () => {
    expect(aqiGaps(undefined)).toBe("");
    expect(aqiGaps([1])).toBe("");
    expect(aqiGaps({ NO2: "WAT" })).toBe("NO2 (brak)");
  });
});

describe("airIndexView", () => {
  it("returns null without a block (older backend) - never throws", () => {
    expect(airIndexView(undefined, NOW, NOW)).toBeNull();
    expect(airIndexView(null, NOW, NOW)).toBeNull();
    expect(airIndexView("GOOD", NOW, NOW)).toBeNull();
    expect(airIndexView([], NOW, NOW)).toBeNull();
  });

  it("shows label, step and dominant pollutant for a complete index", () => {
    const v = airIndexView(block({ level: "POOR", dominant: ["PM10"] }), NOW, NOW)!;
    expect(v.level).toBe("POOR");
    expect(v.label).toBe("Zła");
    expect(v.step).toBe(4);
    expect(v.icon).toBe("✕"); // not colour alone
    expect(v.headline).toBe("Indeks jakości powietrza: zła");
    expect(v.detail).toBe("decyduje: PM10");
  });

  it("an incomplete set is only a lower bound and says what is missing", () => {
    const v = airIndexView(
      block({ level: "MODERATE", complete: false, missing: { O3: "MISSING" } }),
      NOW,
      NOW,
    )!;
    expect(v.headline).toBe("Indeks jakości powietrza: co najmniej umiarkowana");
    expect(v.note).toContain("Niepełny zestaw");
    expect(v.note).toContain("O3 (brak)");
  });

  it("null level is 'brak indeksu' with the gaps, never a good-looking default", () => {
    const v = airIndexView(
      block({ level: null, complete: false, missing: { NO2: "MISSING" }, dominant: [] }),
      NOW,
      NOW,
    )!;
    expect(v.level).toBeNull();
    expect(v.step).toBeNull();
    expect(v.icon).toBe("?");
    expect(v.headline).toBe("Indeks jakości powietrza: brak indeksu");
    expect(v.detail).toBe("brak danych: NO2 (brak)");
  });

  it("an unknown level string degrades to no index", () => {
    const v = airIndexView({ ...block(), level: "WHATEVER" }, NOW, NOW)!;
    expect(v.level).toBeNull();
  });

  it("stops claiming after valid_until (rule #8)", () => {
    const expired = Date.parse(LATER) + 1;
    const v = airIndexView(block(), expired, NOW)!;
    expect(v.level).toBeNull();
    expect(v.detail).toContain("zestarzeć");
    expect(airIndexView(block(), Date.parse(LATER), NOW)!.level).toBe("GOOD");
  });

  it("falls back to response age without a usable valid_until", () => {
    const b = block({ valid_until: null });
    expect(airIndexView(b, NOW + AQI_FALLBACK_MAX_AGE_MS, NOW)!.level).toBe("GOOD");
    expect(airIndexView(b, NOW + AQI_FALLBACK_MAX_AGE_MS + 1, NOW)!.level).toBeNull();
    const garbage = { ...b, valid_until: "garbage" };
    expect(airIndexView(garbage, NOW + AQI_FALLBACK_MAX_AGE_MS + 1, NOW)!.level).toBeNull();
  });

  it("tolerates missing fields", () => {
    const v = airIndexView({ level: "FAIR", valid_until: LATER }, NOW, NOW)!;
    expect(v.level).toBe("FAIR");
    expect(v.detail).toBeNull();
    expect(v.note).toContain("Niepełny zestaw");
  });
});
